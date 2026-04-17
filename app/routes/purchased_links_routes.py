from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.models.models import Backlink, BacklinkCheckHistory, Site, Task, AppLog
from app.services.link_analysis_service import link_analysis_service
from app.services.link_service import link_service
from app.utils.time import utcnow


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchased-links", tags=["purchased-links"])


class PurchasedLinkCreatePayload(BaseModel):
    source_url: str
    target_url: Optional[str] = None
    anchor: Optional[str] = None
    link_type: Optional[str] = None
    domain_score: Optional[int] = None


@router.get("")
async def list_purchased_links(
    site_id: int = Query(...),
    status: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=500),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    site = await db.get(Site, int(site_id))
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await link_service.list(
        db,
        site_id=int(site_id),
        source="purchased",
        status=status,
        link_type=None,
        toxic=None,
        compare=None,
        q=q,
        limit=limit,
    )


@router.post("/add")
async def add_purchased_link(
    payload: PurchasedLinkCreatePayload,
    site_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    site = await db.get(Site, int(site_id))
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    target = (payload.target_url or "").strip()
    if not target:
        target = f"https://{site.domain.strip().rstrip('/')}/"
    row = await link_service.upsert(
        db,
        site_id=int(site_id),
        source_url=payload.source_url,
        target_url=target,
        anchor=payload.anchor,
        link_type=payload.link_type,
        domain_score=payload.domain_score,
        source="purchased",
    )
    return {"ok": True, "id": int(row.id)}


@router.get("/history")
async def purchased_link_history(
    backlink_id: int = Query(...),
    limit: int = Query(default=200),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    limit = max(1, min(500, int(limit)))
    b = await db.get(Backlink, int(backlink_id))
    if not b:
        raise HTTPException(status_code=404, detail="Not found")
    rows = (
        await db.execute(
            select(BacklinkCheckHistory)
            .where(BacklinkCheckHistory.backlink_id == int(backlink_id))
            .order_by(BacklinkCheckHistory.checked_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "ok": True,
        "backlink_id": int(backlink_id),
        "items": [
            {
                "checked_at": r.checked_at.isoformat() if r.checked_at else None,
                "http_status": r.http_status,
                "status": r.status,
                "link_type": r.link_type,
                "outgoing_links": r.outgoing_links,
                "content_length": r.content_length,
                "domain_score": r.domain_score,
                "toxic_score": r.toxic_score,
                "toxic_flag": r.toxic_flag,
            }
            for r in rows
        ],
    }


@router.post("/monitor")
async def monitor_purchased_links(
    background: BackgroundTasks,
    site_id: int = Query(...),
    limit: int = Query(default=50),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    site = await db.get(Site, int(site_id))
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    limit = max(1, min(500, int(limit)))

    task = Task(site_id=int(site_id), title=f"Мониторинг купленных ссылок: {site.domain}", description=None, status="in_progress")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    db.add(
        AppLog(
            level="INFO",
            category="purchased_links",
            method="POST",
            path="/api/purchased-links/monitor",
            status_code=None,
            message=f"scheduled purchased links monitor site_id={site_id} task_id={task.id}",
            created_at=utcnow(),
        )
    )
    await db.commit()

    async def _job():
        async with AsyncSessionLocal() as job_db:
            try:
                rows = (
                    await job_db.execute(
                        select(Backlink)
                        .where(Backlink.site_id == int(site_id), Backlink.source == "purchased")
                        .order_by(Backlink.last_checked.asc().nullsfirst(), Backlink.first_seen.asc())
                        .limit(limit)
                    )
                ).scalars().all()

                for b in rows:
                    await link_analysis_service.analyze_one(job_db, backlink=b)

                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "done"
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="INFO",
                        category="purchased_links",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"purchased links monitor done site_id={site_id} task_id={task.id} checked={len(rows)}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()
            except Exception as e:
                logger.exception(f"Purchased links monitor failed site_id={site_id}: {e}")
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "todo"
                    t.description = "Ошибка мониторинга купленных ссылок. Проверьте логи."
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="ERROR",
                        category="purchased_links",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"purchased links monitor failed site_id={site_id} task_id={task.id}: {e}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()

    if settings.TESTING:
        await _job()
        return {"ok": True, "scheduled": False, "task_id": int(task.id)}
    background.add_task(_job)
    return {"ok": True, "scheduled": True, "task_id": int(task.id)}

