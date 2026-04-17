from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Site
from app.services.webmaster_service import webmaster_service


router = APIRouter(prefix="/webmaster", tags=["webmaster"])


class GSCConnectRequest(BaseModel):
    site_url: str
    access_token: str


class YandexConnectRequest(BaseModel):
    host_id: str
    oauth_token: str


@router.post("/sites/{site_id}/google/connect")
async def connect_google(site_id: int, payload: GSCConnectRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Save token-based credentials for Google Search Console.
    """
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    rec = await webmaster_service.upsert_gsc_token(db, site_id, site_url=payload.site_url, access_token=payload.access_token)
    return {"ok": True, "site_id": site_id, "enabled": rec.enabled}


@router.post("/sites/{site_id}/yandex/connect")
async def connect_yandex(site_id: int, payload: YandexConnectRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Save token-based credentials for Yandex Webmaster.
    """
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    rec = await webmaster_service.upsert_yandex_token(db, site_id, host_id=payload.host_id, oauth_token=payload.oauth_token)
    return {"ok": True, "site_id": site_id, "enabled": rec.enabled}
