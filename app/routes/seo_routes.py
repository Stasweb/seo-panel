from fastapi import APIRouter
from app.services.seo_service import seo_service
from app.schemas.schemas import DensityRequest, MetaRequest, AuditRequest, AuditResult
from typing import Any, Dict, List

router = APIRouter(prefix="/seo", tags=["seo"])

@router.post("/density")
async def keyword_density(payload: DensityRequest) -> Dict[str, Any]:
    """
    Calculate keyword density.
    """
    density = seo_service.calculate_keyword_density(payload.text)
    return {"density": density}

@router.post("/meta")
async def generate_meta(payload: MetaRequest) -> Dict[str, Any]:
    """
    Generate meta description.
    """
    meta = seo_service.generate_meta_description(payload.content, max_length=payload.max_length)
    return {"meta": meta, "length": len(meta)}

@router.post("/audit", response_model=AuditResult)
async def audit_url(payload: AuditRequest):
    """
    Quick audit for a single URL.
    """
    return await seo_service.check_url(payload.url)
