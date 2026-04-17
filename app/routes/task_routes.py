from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import Task, Site
from app.services.organization_service import organization_service


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/")
async def list_tasks(
    request: Request,
    status: Optional[str] = Query(default=None),
    site_id: Optional[int] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    sort: str = Query(default="created_desc"),
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
    if st not in {None, "todo", "in_progress", "done"}:
        st = None
    pr = (priority or "").strip().lower() or None
    if pr not in {None, "low", "normal", "high"}:
        pr = None
    query = (q or "").strip()
    if len(query) > 200:
        query = query[:200]
    sort_key = (sort or "created_desc").strip().lower()
    if sort_key not in {"created_desc", "created_asc", "priority_desc"}:
        sort_key = "created_desc"

    stmt = select(Task, Site.domain).join(Site, Task.site_id == Site.id)
    if role != "admin":
        stmt = stmt.where(Site.organization_id == org_id)
    if site_id:
        stmt = stmt.where(Task.site_id == int(site_id))
    if st:
        stmt = stmt.where(Task.status == st)
    if pr:
        stmt = stmt.where(Task.priority == pr)
    if query:
        like = f"%{query}%"
        stmt = stmt.where((Task.title.ilike(like)) | (Task.description.ilike(like)))
    if sort_key == "priority_desc":
        stmt = stmt.order_by(
            (Task.priority == "high").desc(),
            (Task.priority == "normal").desc(),
            Task.id.desc(),
        )
    elif sort_key == "created_asc":
        stmt = stmt.order_by(Task.id.asc())
    else:
        stmt = stmt.order_by(Task.id.desc())
    stmt = stmt.limit(limit)

    rows = (await db.execute(stmt)).all()
    items: List[Dict[str, Any]] = []
    for task, domain in rows:
        items.append(
            {
                "id": int(task.id),
                "site_id": int(task.site_id),
                "site_domain": str(domain or ""),
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": getattr(task, "priority", "normal"),
                "source_url": getattr(task, "source_url", None),
                "deep_audit_report_id": getattr(task, "deep_audit_report_id", None),
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
        )

    return {"items": items, "limit": limit, "status": st, "site_id": site_id, "priority": pr, "q": query, "sort": sort_key}


@router.get("/{task_id}")
async def get_task(task_id: int, request: Request, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id

    stmt = select(Task, Site.domain).join(Site, Task.site_id == Site.id).where(Task.id == int(task_id))
    if role != "admin":
        stmt = stmt.where(Site.organization_id == org_id)
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    task, domain = row
    return {
        "id": int(task.id),
        "site_id": int(task.site_id),
        "site_domain": str(domain or ""),
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": getattr(task, "priority", "normal"),
        "source_url": getattr(task, "source_url", None),
        "deep_audit_report_id": getattr(task, "deep_audit_report_id", None),
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


class TaskUpdatePayload(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None


@router.patch("/{task_id}")
async def update_task(task_id: int, payload: TaskUpdatePayload, request: Request, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    row = await db.get(Task, int(task_id))
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if payload.status is not None:
        st = (payload.status or "").strip().lower()
        if st not in {"todo", "in_progress", "done"}:
            raise HTTPException(status_code=400, detail="Invalid status")
        row.status = st
    if payload.priority is not None:
        pr = (payload.priority or "").strip().lower()
        if pr not in {"low", "normal", "high"}:
            raise HTTPException(status_code=400, detail="Invalid priority")
        row.priority = pr
    db.add(row)
    await db.commit()
    return {"ok": True}
