from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Site
from app.services.integrations_service import integrations_service


router = APIRouter(prefix="/integrations", tags=["integrations"])


class AhrefsSaveRequest(BaseModel):
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    clear: Optional[bool] = None


@router.get("")
async def integrations_overview(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    return await integrations_service.list_overview(db)


@router.post("/{site_id}/ahrefs-save")
async def save_ahrefs(site_id: int, payload: AhrefsSaveRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await integrations_service.save_ahrefs(
        db,
        site_id=site_id,
        api_key=payload.api_key,
        enabled=payload.enabled,
        clear=bool(payload.clear),
    )


@router.get("/{site_id}/ahrefs")
async def get_ahrefs(site_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return {"ok": True, "site_id": site_id, "ahrefs": await integrations_service.get_ahrefs(db, site_id=site_id)}
