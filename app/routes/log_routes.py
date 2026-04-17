from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import AppLog
from app.utils.time import utcnow


router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
async def list_logs(
    level: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    hours: int = Query(default=24),
    limit: int = Query(default=500),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    hours = max(1, min(24 * 30, int(hours)))
    limit = max(1, min(5000, int(limit)))
    cutoff = utcnow() - timedelta(hours=hours)

    stmt = select(AppLog).where(AppLog.created_at >= cutoff).order_by(AppLog.created_at.desc()).limit(limit)
    if level:
        stmt = stmt.where(AppLog.level == level.upper())
    if category:
        stmt = stmt.where(AppLog.category == category.lower())

    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "level": r.level,
            "category": r.category,
            "method": r.method,
            "path": r.path,
            "status_code": r.status_code,
            "message": r.message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/cleanup")
async def cleanup_logs(period: str = Query(default="1d"), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    p = (period or "1d").strip().lower()
    if p == "all":
        stmt = delete(AppLog)
    elif p == "1h":
        cutoff = utcnow() - timedelta(hours=1)
        stmt = delete(AppLog).where(AppLog.created_at < cutoff)
    else:
        cutoff = utcnow() - timedelta(days=1)
        stmt = delete(AppLog).where(AppLog.created_at < cutoff)
    res = await db.execute(stmt)
    await db.commit()
    return {"ok": True, "deleted": int(getattr(res, "rowcount", 0) or 0), "period": p}
