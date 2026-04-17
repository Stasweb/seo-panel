from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db, AsyncSessionLocal
from app.models.models import Site, SiteScanHistory, SeoHealthScoreHistory, MetricHistory, Task, SEOAudit, AppLog
from app.services.site_scan_service import site_scan_service
from app.services.robots_service import robots_service
from app.services.sitemap_service import sitemap_service
from app.services.metrics_service import metrics_service
from app.services.tech_audit_service import tech_audit_service
from app.services.auto_task_service import auto_task_service
from app.core.config import settings
from app.utils.user_agents import resolve_user_agent
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


router = APIRouter(tags=["scans"])


def _site_priority_delay_ms(site: Site) -> int:
    p = str(getattr(site, "scan_priority", "normal") or "normal").strip().lower()
    if p == "high":
        return 0
    if p == "low":
        return 800
    return 300


def _site_pause_ms(site: Site) -> int:
    base = int(getattr(site, "scan_pause_ms", 0) or 0)
    base = max(0, min(10000, base))
    return min(12000, base + _site_priority_delay_ms(site))


@router.post("/sites/{site_id}/scan")
async def run_full_site_scan(
    site_id: int,
    background: BackgroundTasks,
    ua: Optional[str] = Query(default=None),
    custom_ua: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger a full site scan asynchronously.

    The scan runs in background and persists results into SiteScanHistory.
    """
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    task = Task(site_id=site_id, title=f"Скан сайта: {site.domain}", description=None, status="in_progress")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    db.add(
        AppLog(
            level="INFO",
            category="scan",
            method="POST",
            path=f"/api/sites/{site_id}/scan",
            status_code=None,
            message=f"scheduled scan site_id={site_id} task_id={task.id}",
            created_at=utcnow(),
        )
    )
    await db.commit()
    logger.info("scan_scheduled site_id=%s task_id=%s ua=%s", site_id, task.id, ua or "default")

    if settings.TESTING:
        task.status = "done"
        db.add(task)
        db.add(
            AppLog(
                level="INFO",
                category="scan",
                method=None,
                path=None,
                status_code=None,
                message=f"scan done (testing) site_id={site_id} task_id={task.id}",
                created_at=utcnow(),
            )
        )
        await db.commit()
        return {"ok": True, "scheduled": False, "site_id": site_id, "task_id": task.id}

    async def _job():
        async with AsyncSessionLocal() as job_db:
            s = await job_db.get(Site, site_id)
            if not s:
                return
            try:
                ua_choice = ua if ua is not None else getattr(s, "user_agent_choice", None)
                custom_choice = custom_ua if custom_ua is not None else getattr(s, "custom_user_agent", None)
                pause_s = float(_site_pause_ms(s)) / 1000.0
                if pause_s > 0:
                    await asyncio.sleep(pause_s)
                await site_scan_service.scan_site(
                    job_db,
                    s,
                    user_agent_choice=ua_choice,
                    custom_user_agent=custom_choice,
                )
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "done"
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="INFO",
                        category="scan",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"scan done site_id={site_id} task_id={task.id}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()
            except Exception as e:
                logger.exception(f"Scan job failed site_id={site_id}: {e}")
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "todo"
                    t.description = "Ошибка сканирования. Проверьте логи."
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="ERROR",
                        category="scan",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"scan failed site_id={site_id} task_id={task.id}: {e}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()

    background.add_task(_job)
    return {"ok": True, "scheduled": True, "site_id": site_id, "task_id": task.id}


@router.post("/sites/scan-all")
async def run_full_audit_for_all_sites(
    background: BackgroundTasks,
    ua: Optional[str] = Query(default=None),
    custom_ua: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger full audit for all sites.
    Runs sequentially in background to avoid server overload.
    """
    sites = (await db.execute(select(Site.id, Site.domain).order_by(Site.id.asc()))).all()
    site_ids = [int(r[0]) for r in sites]
    task_ids: Dict[int, int] = {}
    for r in sites:
        sid = int(r[0])
        domain = str(r[1] or "")
        t = Task(site_id=sid, title=f"Полный аудит: {domain}", description=None, status="in_progress")
        db.add(t)
        await db.flush()
        task_ids[sid] = int(t.id)
    await db.commit()
    logger.info("scan_all_scheduled count=%s", len(site_ids))

    if settings.TESTING:
        for sid in site_ids:
            t = await db.get(Task, task_ids.get(sid))
            if t:
                t.status = "done"
                db.add(t)
        await db.commit()
        return {"ok": True, "scheduled": False, "count": len(site_ids)}

    async def _job():
        async with AsyncSessionLocal() as job_db:
            for sid in site_ids:
                try:
                    s = await job_db.get(Site, sid)
                    if not s:
                        continue
                    ua_choice = ua if ua is not None else getattr(s, "user_agent_choice", None)
                    custom_choice = custom_ua if custom_ua is not None else getattr(s, "custom_user_agent", None)
                    pause_ms = _site_pause_ms(s)
                    await tech_audit_service.run(
                        job_db,
                        site=s,
                        user_agent_choice=ua_choice,
                        custom_user_agent=custom_choice,
                        respect_robots_txt=(getattr(s, "respect_robots_txt", True) is not False),
                        use_sitemap=(getattr(s, "use_sitemap", True) is not False),
                        pause_ms=pause_ms,
                    )
                    await auto_task_service.sync_site(job_db, site_id=sid, max_tasks=8, include_low=False)
                    t = await job_db.get(Task, task_ids.get(sid))
                    if t:
                        t.status = "done"
                        job_db.add(t)
                    job_db.add(
                        AppLog(
                            level="INFO",
                            category="audit",
                            method=None,
                            path=None,
                            status_code=None,
                            message=f"audit done site_id={sid} task_id={task_ids.get(sid)}",
                            created_at=utcnow(),
                        )
                    )
                    await job_db.commit()
                    await asyncio.sleep(float(pause_ms) / 1000.0)
                except Exception as e:
                    logger.exception(f"Scan failed for site_id={sid}: {e}")
                    t = await job_db.get(Task, task_ids.get(sid))
                    if t:
                        t.status = "todo"
                        t.description = "Ошибка полного аудита. Проверьте логи."
                        job_db.add(t)
                    job_db.add(
                        AppLog(
                            level="ERROR",
                            category="audit",
                            method=None,
                            path=None,
                            status_code=None,
                            message=f"audit failed site_id={sid} task_id={task_ids.get(sid)}: {e}",
                            created_at=utcnow(),
                        )
                    )
                    await job_db.commit()

    background.add_task(_job)
    return {"ok": True, "scheduled": True, "count": len(site_ids)}


@router.get("/sites/{site_id}/scan-history")
async def get_scan_history(site_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Return scan history for charts and UI.
    """
    rows = await db.execute(
        select(SiteScanHistory)
        .where(SiteScanHistory.site_id == site_id)
        .order_by(SiteScanHistory.created_at.asc())
        .limit(200)
    )
    items = rows.scalars().all()
    return {
        "site_id": site_id,
        "items": [
            {
                "created_at": i.created_at.isoformat(),
                "status_code": i.status_code,
                "response_time_ms": i.response_time_ms,
                "title_length": i.title_length,
                "h1_present": i.h1_present,
                "indexed": i.indexed,
                "health_score": i.health_score,
            }
            for i in items
        ],
        "labels": [i.created_at.isoformat() for i in items],
        "response_time_ms": [i.response_time_ms for i in items],
        "status_code": [i.status_code for i in items],
        "indexed": [1 if i.indexed else 0 for i in items],
        "health_score": [i.health_score for i in items],
    }


@router.post("/sites/{site_id}/scan-history/clear")
async def clear_scan_history(
    site_id: int,
    request: Request,
    confirm: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if (confirm or "").strip().upper() != "DELETE":
        raise HTTPException(status_code=400, detail="Confirm required")
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    r1 = await db.execute(delete(SiteScanHistory).where(SiteScanHistory.site_id == int(site_id)))
    r2 = await db.execute(delete(SeoHealthScoreHistory).where(SeoHealthScoreHistory.site_id == int(site_id)))
    await db.commit()
    return {
        "ok": True,
        "site_id": int(site_id),
        "deleted_scan_rows": int(getattr(r1, "rowcount", 0) or 0),
        "deleted_health_rows": int(getattr(r2, "rowcount", 0) or 0),
    }


@router.post("/sites/{site_id}/robots-check")
async def robots_check(
    site_id: int,
    ua: Optional[str] = Query(default=None),
    custom_ua: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Check robots.txt and persist result into MetricHistory.
    """
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if getattr(site, "respect_robots_txt", True) is False:
        result = {"status": "SKIPPED", "detail": "robots check disabled in site settings"}
        await metrics_service.save(db, site_id=site_id, metric_type="robots", value=result)
        return result

    ua_choice = ua if ua is not None else getattr(site, "user_agent_choice", None)
    custom_choice = custom_ua if custom_ua is not None else getattr(site, "custom_user_agent", None)
    user_agent = resolve_user_agent(ua_choice, custom_choice, settings.USER_AGENT)
    result = await robots_service.fetch_and_analyze(site.domain, user_agent=user_agent)
    await metrics_service.save(db, site_id=site_id, metric_type="robots", value=result)
    await auto_task_service.sync_site(db, site_id=site_id, max_tasks=8, include_low=False)
    return result


@router.post("/sites/{site_id}/sitemap-check")
async def sitemap_check(
    site_id: int,
    ua: Optional[str] = Query(default=None),
    custom_ua: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Check sitemap.xml (or sitemap_index.xml) and persist result into MetricHistory.
    """
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if getattr(site, "use_sitemap", True) is False:
        result = {"status": "SKIPPED", "detail": "sitemap check disabled in site settings"}
        await metrics_service.save(db, site_id=site_id, metric_type="sitemap", value=result)
        return result

    ua_choice = ua if ua is not None else getattr(site, "user_agent_choice", None)
    custom_choice = custom_ua if custom_ua is not None else getattr(site, "custom_user_agent", None)
    user_agent = resolve_user_agent(ua_choice, custom_choice, settings.USER_AGENT)
    result = await sitemap_service.fetch_and_analyze(site.domain, user_agent=user_agent)
    await metrics_service.save(db, site_id=site_id, metric_type="sitemap", value=result)
    await auto_task_service.sync_site(db, site_id=site_id, max_tasks=8, include_low=False)
    return result


@router.post("/sites/{site_id}/tech-audit")
async def run_tech_audit(
    site_id: int,
    background: BackgroundTasks,
    ua: Optional[str] = Query(default=None),
    custom_ua: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Run full technical audit asynchronously and persist into SiteScanHistory + MetricHistory.
    """
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    task = Task(site_id=site_id, title=f"Тех. аудит: {site.domain}", description=None, status="in_progress")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    db.add(
        AppLog(
            level="INFO",
            category="audit",
            method="POST",
            path=f"/api/sites/{site_id}/tech-audit",
            status_code=None,
            message=f"scheduled tech audit site_id={site_id} task_id={task.id}",
            created_at=utcnow(),
        )
    )
    await db.commit()
    logger.info("tech_audit_scheduled site_id=%s task_id=%s ua=%s", site_id, task.id, ua or "default")

    if settings.TESTING:
        task.status = "done"
        db.add(task)
        db.add(
            AppLog(
                level="INFO",
                category="audit",
                method=None,
                path=None,
                status_code=None,
                message=f"tech audit done (testing) site_id={site_id} task_id={task.id}",
                created_at=utcnow(),
            )
        )
        await db.commit()
        return {"ok": True, "scheduled": False, "site_id": site_id, "task_id": task.id}

    async def _job():
        async with AsyncSessionLocal() as job_db:
            s = await job_db.get(Site, site_id)
            if not s:
                return
            try:
                ua_choice = ua if ua is not None else getattr(s, "user_agent_choice", None)
                custom_choice = custom_ua if custom_ua is not None else getattr(s, "custom_user_agent", None)
                pause_ms = _site_pause_ms(s)
                await tech_audit_service.run(
                    job_db,
                    site=s,
                    user_agent_choice=ua_choice,
                    custom_user_agent=custom_choice,
                    respect_robots_txt=(getattr(s, "respect_robots_txt", True) is not False),
                    use_sitemap=(getattr(s, "use_sitemap", True) is not False),
                    pause_ms=pause_ms,
                )
                await auto_task_service.sync_site(job_db, site_id=site_id, max_tasks=8, include_low=False)
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "done"
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="INFO",
                        category="audit",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"tech audit done site_id={site_id} task_id={task.id}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()
            except Exception as e:
                logger.exception(f"Tech audit job failed site_id={site_id}: {e}")
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "todo"
                    t.description = "Ошибка тех. аудита. Проверьте логи."
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="ERROR",
                        category="audit",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"tech audit failed site_id={site_id} task_id={task.id}: {e}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()

    background.add_task(_job)
    return {"ok": True, "scheduled": True, "site_id": site_id, "task_id": task.id}


@router.post("/scans/cleanup")
async def cleanup_scans(
    hours: int = Query(default=48),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    hours = max(1, min(24 * 30, int(hours)))
    cutoff = utcnow() - timedelta(hours=hours)
    res1 = await db.execute(delete(SiteScanHistory).where(SiteScanHistory.created_at < cutoff))
    res2 = await db.execute(delete(SEOAudit).where(SEOAudit.last_check < cutoff))
    await db.commit()
    return {
        "ok": True,
        "cutoff": cutoff.isoformat(),
        "deleted_scan_rows": int(getattr(res1, "rowcount", 0) or 0),
        "deleted_audit_rows": int(getattr(res2, "rowcount", 0) or 0),
    }


@router.get("/sites/{site_id}/metric-history")
async def metric_history(
    site_id: int,
    metric_type: str,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return generic metric history (robots/sitemap/tech_audit) for charts.
    """
    limit = max(1, min(500, int(limit)))
    rows = await db.execute(
        select(MetricHistory)
        .where(MetricHistory.site_id == site_id, MetricHistory.metric_type == metric_type)
        .order_by(MetricHistory.created_at.asc())
        .limit(limit)
    )
    items = rows.scalars().all()
    return {
        "site_id": site_id,
        "metric_type": metric_type,
        "items": [
            {"created_at": i.created_at.isoformat(), "value": i.value_json}
            for i in items
        ],
    }
