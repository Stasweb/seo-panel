from __future__ import annotations

import os
import platform
import sys
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from app.core.config import settings
from app.utils.time import utcnow

_START_MONO = time.monotonic()


def _parse_sqlite_path(db_url: str) -> Optional[str]:
    u = (db_url or "").strip()
    if not u:
        return None
    if not u.startswith("sqlite"):
        return None
    try:
        p = urlparse(u)
        path = p.path or ""
        while path.startswith("/"):
            path = path[1:]
        if not path:
            return None
        return os.path.abspath(path)
    except Exception:
        return None


def _file_size_bytes(path: str) -> Optional[int]:
    try:
        return int(os.path.getsize(path))
    except Exception:
        return None


class SystemInfoService:
    def get(self) -> Dict[str, Any]:
        now = utcnow()
        up_s = int(time.monotonic() - _START_MONO)

        db_url = (settings.DATABASE_URL or "").strip()
        sqlite_path = _parse_sqlite_path(db_url)
        db_size = _file_size_bytes(sqlite_path) if sqlite_path else None

        return {
            "ok": True,
            "checked_at": now.isoformat(),
            "uptime_seconds": up_s,
            "python": {"version": sys.version.split()[0], "implementation": platform.python_implementation()},
            "os": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
            "db": {"url": db_url, "sqlite_path": sqlite_path, "size_bytes": db_size},
            "app": {"port": int(settings.PORT)},
        }


system_info_service = SystemInfoService()
