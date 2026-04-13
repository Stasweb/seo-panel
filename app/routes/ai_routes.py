from __future__ import annotations

from fastapi import APIRouter
from typing import Any, Dict

from app.services.ai_service import ai_service
from app.schemas.schemas import MetaRequest, DensityRequest, TitleRequest


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/meta")
async def ai_meta(payload: MetaRequest) -> Dict[str, Any]:
    """
    Pseudo-AI meta description generator (no paid APIs).
    """
    return ai_service.generate_meta(payload.content, max_length=payload.max_length)


@router.post("/keywords")
async def ai_keywords(payload: DensityRequest) -> Dict[str, Any]:
    """
    Pseudo-AI keyword suggestions (top words).
    """
    return ai_service.keyword_suggestions(payload.text, limit=10)


@router.post("/title-check")
async def ai_title_check(payload: TitleRequest) -> Dict[str, Any]:
    """
    Title length optimizer and recommendations.
    """
    return ai_service.title_check(payload.title)
