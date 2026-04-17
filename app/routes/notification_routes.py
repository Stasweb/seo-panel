from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notification_service import notification_service


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/recent")
async def recent_notifications(
    request: Request,
    limit: int = Query(default=20),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    org_id = getattr(request.state, "organization_id", None)
    return await notification_service.list_recent(db, organization_id=org_id, limit=limit)


@router.post("/{event_id}/seen")
async def mark_seen(event_id: int, request: Request, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    ok = await notification_service.mark_seen(db, event_id=event_id)
    return {"ok": ok}
