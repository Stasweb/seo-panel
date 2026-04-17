from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.recommendations_service import recommendations_service


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/{site_id}")
async def get_recommendations(site_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await recommendations_service.generate(db, site_id=site_id, use_ai=True)
