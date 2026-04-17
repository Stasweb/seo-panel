from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Site, GSCAccount, YandexAccount, AhrefsAccount
from app.utils.time import utcnow


class IntegrationsService:
    async def list_overview(self, db: AsyncSession) -> List[Dict[str, Any]]:
        sites = (await db.execute(select(Site).order_by(Site.id.asc()))).scalars().all()
        ahrefs = (await db.execute(select(AhrefsAccount))).scalars().all()

        a_by_site = {r.site_id: r for r in ahrefs}

        out: List[Dict[str, Any]] = []
        for s in sites:
            a = a_by_site.get(s.id)
            out.append(
                {
                    "site_id": s.id,
                    "domain": s.domain,
                    "gsc": {
                        "mode": "manual",
                        "connected": False,
                        "site_url": None,
                        "selected_account_email": None,
                        "updated_at": None,
                    },
                    "yandex": {
                        "mode": "manual",
                        "connected": False,
                        "host_id": None,
                        "selected_account_login": None,
                        "updated_at": None,
                    },
                    "ahrefs": {
                        "connected": bool(a and a.enabled and a.api_key),
                        "updated_at": a.updated_at.isoformat() if a and a.updated_at else None,
                    },
                }
            )
        return out

    async def is_gsc_connected(self, db: AsyncSession, *, site_id: int) -> bool:
        row = (await db.execute(select(GSCAccount).where(GSCAccount.site_id == site_id))).scalars().first()
        return bool(row and row.connected)

    async def is_yandex_connected(self, db: AsyncSession, *, site_id: int) -> bool:
        row = (await db.execute(select(YandexAccount).where(YandexAccount.site_id == site_id))).scalars().first()
        return bool(row and row.connected)

    async def get_ahrefs(self, db: AsyncSession, *, site_id: int) -> Dict[str, Any]:
        row = (await db.execute(select(AhrefsAccount).where(AhrefsAccount.site_id == site_id))).scalars().first()
        return {
            "connected": bool(row and row.enabled and row.api_key),
            "enabled": bool(row.enabled) if row else False,
            "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
        }

    async def get_ahrefs_credentials(self, db: AsyncSession, *, site_id: int) -> Dict[str, Any]:
        row = (await db.execute(select(AhrefsAccount).where(AhrefsAccount.site_id == site_id))).scalars().first()
        return {
            "enabled": bool(row and row.enabled),
            "api_key": (row.api_key or "") if row else "",
            "connected": bool(row and row.enabled and row.api_key),
        }

    async def save_ahrefs(self, db: AsyncSession, *, site_id: int, api_key: Optional[str], enabled: Optional[bool], clear: bool = False) -> Dict[str, Any]:
        now = utcnow()
        row = (await db.execute(select(AhrefsAccount).where(AhrefsAccount.site_id == site_id))).scalars().first()
        if not row:
            row = AhrefsAccount(site_id=site_id)
        if clear:
            row.api_key = None
            row.enabled = False
        else:
            if enabled is not None:
                row.enabled = bool(enabled)
            if api_key is not None:
                row.api_key = api_key.strip() or None
        row.updated_at = now
        db.add(row)
        await db.commit()
        return {"ok": True, "site_id": site_id}


integrations_service = IntegrationsService()
