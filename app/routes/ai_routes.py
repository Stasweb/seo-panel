from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import ai_service
from app.schemas.schemas import MetaRequest, DensityRequest, TitleRequest
from app.core.database import get_db
from app.services.ai_config_service import ai_config_service
from app.services.ollama_client import ollama_client
from app.services.ai_runtime_service import ai_runtime_service


router = APIRouter(prefix="/ai", tags=["ai"])

class AIConfigIn(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None

@router.get("/providers")
async def ai_providers(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await ai_runtime_service.resolve(db)


@router.get("/models")
async def ai_models(provider: str = Query(default="ollama"), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    p = (provider or "").strip().lower()
    if p != "ollama":
        return {"provider": p, "models": []}
    ok = await ollama_client.is_available()
    models = await ollama_client.list_models() if ok else []
    return {"provider": "ollama", "available": ok, "models": models}


@router.get("/config")
async def ai_config(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await ai_runtime_service.resolve(db)


@router.post("/config")
async def ai_config_save(payload: AIConfigIn, request: Request, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await ai_config_service.set_config(db, provider=payload.provider, model=payload.model)
    return await ai_runtime_service.resolve(db)


@router.post("/meta")
async def ai_meta(payload: MetaRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Meta description generator: uses local LLM if available, otherwise pseudo-AI fallback.
    """
    resolved = await ai_runtime_service.resolve(db)
    if resolved["effective_provider"] == "ollama" and resolved["effective_model"]:
        out = await ai_service.generate_meta_ai(payload.content, max_length=payload.max_length, model=resolved["effective_model"])
        if out is not None:
            return out
    return ai_service.generate_meta(payload.content, max_length=payload.max_length)


@router.post("/keywords")
async def ai_keywords(payload: DensityRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Keyword suggestions: uses local LLM if available, otherwise pseudo-AI fallback.
    """
    resolved = await ai_runtime_service.resolve(db)
    if resolved["effective_provider"] == "ollama" and resolved["effective_model"]:
        out = await ai_service.keyword_suggestions_ai(payload.text, limit=10, model=resolved["effective_model"])
        if out is not None:
            return out
    return ai_service.keyword_suggestions(payload.text, limit=10)


@router.post("/title-check")
async def ai_title_check(payload: TitleRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Title optimizer: uses local LLM if available, otherwise pseudo-AI fallback.
    """
    resolved = await ai_runtime_service.resolve(db)
    if resolved["effective_provider"] == "ollama" and resolved["effective_model"]:
        out = await ai_service.title_check_ai(payload.title, model=resolved["effective_model"])
        if out is not None:
            return out
    return ai_service.title_check(payload.title)
