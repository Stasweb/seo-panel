from __future__ import annotations

import json
import socket
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.http_client import http_service
from app.models.models import IPAddressSnapshot
from app.utils.time import utcnow


def _detect_local_ip() -> Tuple[Optional[str], str, Dict[str, Any]]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            return ip, "udp_socket", {"target": "8.8.8.8:80"}
        finally:
            s.close()
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
            return ip, "hostname", {}
        except Exception:
            return None, "unknown", {}


async def _detect_external_ip() -> Tuple[Optional[str], str, Dict[str, Any]]:
    if settings.TESTING:
        return "203.0.113.10", "test", {}
    url = "https://api.ipify.org?format=json"
    try:
        r = await http_service.get_text(url, cache_key="external_ip:ipify", ttl_seconds=300, timeout=6.0, follow_redirects=True)
        if r.status_code != 200:
            return None, "ipify", {"url": url, "http_status": r.status_code}
        data = json.loads(r.text or "{}")
        ip = data.get("ip") if isinstance(data, dict) else None
        if isinstance(ip, str) and ip.strip():
            return ip.strip(), "ipify", {"url": url}
        return None, "ipify", {"url": url, "parse_error": True}
    except Exception as e:
        return None, "ipify", {"url": url, "error": str(e)}


class IPService:
    async def get_current(self, db: AsyncSession) -> Dict[str, Any]:
        local_ip, local_method, local_details = _detect_local_ip()
        external_ip, external_method, external_details = await _detect_external_ip()

        latest = (await db.execute(select(IPAddressSnapshot).order_by(IPAddressSnapshot.created_at.desc()).limit(1))).scalars().first()
        changed = False
        if not latest:
            changed = True
        else:
            if (latest.local_ip or None) != (local_ip or None) or (latest.external_ip or None) != (external_ip or None):
                changed = True

        if changed:
            snap = IPAddressSnapshot(
                local_ip=local_ip,
                external_ip=external_ip,
                local_method=local_method,
                external_method=external_method,
                details_json={"local": local_details, "external": external_details},
                created_at=utcnow(),
            )
            db.add(snap)
            await db.commit()

        history = (
            await db.execute(select(IPAddressSnapshot).order_by(IPAddressSnapshot.created_at.desc()).limit(200))
        ).scalars().all()

        last_local_change = None
        last_external_change = None
        prev_local = None
        prev_external = None
        for h in reversed(history):
            if prev_local is None:
                prev_local = h.local_ip
                prev_external = h.external_ip
                last_local_change = h.created_at
                last_external_change = h.created_at
                continue
            if h.local_ip != prev_local:
                prev_local = h.local_ip
                last_local_change = h.created_at
            if h.external_ip != prev_external:
                prev_external = h.external_ip
                last_external_change = h.created_at

        return {
            "ok": True,
            "local_ip": local_ip,
            "external_ip": external_ip,
            "local_method": local_method,
            "external_method": external_method,
            "checked_at": utcnow().isoformat(),
            "last_local_change_at": last_local_change.isoformat() if last_local_change else None,
            "last_external_change_at": last_external_change.isoformat() if last_external_change else None,
        }

    async def history(self, db: AsyncSession, *, limit: int = 50) -> Dict[str, Any]:
        limit = max(1, min(200, int(limit)))
        rows = (await db.execute(select(IPAddressSnapshot).order_by(IPAddressSnapshot.created_at.desc()).limit(limit))).scalars().all()
        items = []
        for r in rows:
            items.append(
                {
                    "id": int(r.id),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "local_ip": r.local_ip,
                    "external_ip": r.external_ip,
                    "local_method": r.local_method,
                    "external_method": r.external_method,
                    "details": r.details_json or {},
                }
            )
        return {"ok": True, "items": items}


ip_service = IPService()

