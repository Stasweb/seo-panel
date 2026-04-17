from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import ContentPlan, Site
from app.services.organization_service import organization_service


router = APIRouter(prefix="/content-plans", tags=["content"])


class ContentPlanIn(BaseModel):
    site_id: int
    title: str
    url: Optional[str] = None
    status: str = "idea"


class ContentPlanUpdateIn(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None


@router.get("/")
async def list_content_plans(
    request: Request,
    status: Optional[str] = Query(default="idea"),
    site_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id

    limit = max(1, min(200, int(limit)))
    st = (status or "").strip().lower() or None
    if st not in {None, "idea", "writing", "published"}:
        st = None

    stmt = select(ContentPlan, Site.domain).join(Site, ContentPlan.site_id == Site.id)
    if role != "admin":
        stmt = stmt.where(Site.organization_id == org_id)
    if site_id:
        stmt = stmt.where(ContentPlan.site_id == int(site_id))
    if st:
        stmt = stmt.where(ContentPlan.status == st)
    stmt = stmt.order_by(ContentPlan.id.desc()).limit(limit)

    rows = (await db.execute(stmt)).all()
    items: List[Dict[str, Any]] = []
    for row, domain in rows:
        items.append(
            {
                "id": int(row.id),
                "site_id": int(row.site_id),
                "site_domain": str(domain or ""),
                "title": row.title,
                "url": row.url,
                "status": row.status,
                "publish_date": row.publish_date.isoformat() if row.publish_date else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return {"items": items, "limit": limit, "status": st, "site_id": site_id}


@router.post("/", status_code=201)
async def create_content_plan(payload: ContentPlanIn, request: Request, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    site = await db.get(Site, int(payload.site_id))
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    row = ContentPlan(site_id=int(payload.site_id), title=payload.title, url=(payload.url or None), status=payload.status)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"ok": True, "id": int(row.id)}


@router.patch("/{content_id}")
async def update_content_plan(
    content_id: int,
    payload: ContentPlanUpdateIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    row = await db.get(ContentPlan, int(content_id))
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if payload.title is not None:
        row.title = payload.title
    if payload.url is not None:
        row.url = payload.url or None
    if payload.status is not None:
        row.status = payload.status
    db.add(row)
    await db.commit()
    return {"ok": True}

