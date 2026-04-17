from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import NotificationEvent
from app.utils.time import utcnow


class NotificationService:
    async def create_if_not_recent(
        self,
        db: AsyncSession,
        *,
        organization_id: Optional[int],
        site_id: Optional[int],
        user_id: Optional[int],
        event_type: str,
        severity: str,
        message: str,
        dedup_minutes: int = 120,
    ) -> Optional[NotificationEvent]:
        now = utcnow()
        cutoff = now - timedelta(minutes=max(1, int(dedup_minutes)))
        q = select(NotificationEvent).where(
            NotificationEvent.event_type == event_type,
            NotificationEvent.created_at >= cutoff,
        )
        if site_id is not None:
            q = q.where(NotificationEvent.site_id == site_id)
        if organization_id is not None:
            q = q.where(NotificationEvent.organization_id == organization_id)
        exists = (await db.execute(q.order_by(NotificationEvent.created_at.desc()).limit(1))).scalars().first()
        if exists:
            return None

        row = NotificationEvent(
            organization_id=organization_id,
            site_id=site_id,
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            message=message,
            created_at=now,
            seen=False,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row

    async def list_recent(self, db: AsyncSession, *, organization_id: Optional[int], limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, min(200, int(limit)))
        q = select(NotificationEvent).order_by(NotificationEvent.created_at.desc()).limit(limit)
        if organization_id is not None:
            q = q.where(NotificationEvent.organization_id == organization_id)
        rows = (await db.execute(q)).scalars().all()
        return [
            {
                "id": r.id,
                "organization_id": r.organization_id,
                "site_id": r.site_id,
                "event_type": r.event_type,
                "severity": r.severity,
                "message": r.message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "seen": bool(r.seen),
            }
            for r in rows
        ]

    async def mark_seen(self, db: AsyncSession, *, event_id: int) -> bool:
        row = await db.get(NotificationEvent, event_id)
        if not row:
            return False
        row.seen = True
        db.add(row)
        await db.commit()
        return True


notification_service = NotificationService()
