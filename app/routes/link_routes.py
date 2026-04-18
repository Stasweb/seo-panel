from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, Request
from pydantic import BaseModel
from sqlalchemy import select, func, delete

from app.core.database import AsyncSessionLocal, get_db
from app.core.config import settings
from app.models.models import Site, MetricHistory, Backlink, BacklinkStatusHistory, Task, AppLog
from app.utils.time import utcnow
from app.services.integrations_service import integrations_service
from app.services.link_analysis_service import link_analysis_service
from app.services.link_import_service import link_import_service
from app.services.link_service import link_service
from app.services.ahrefs_service import ahrefs_service
from app.services.metrics_service import metrics_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/links", tags=["links"])


async def _fetch_gsc_links(db: AsyncSession, *, site_id: int) -> List[Tuple[str, str, Optional[str], Optional[str]]]:
    connected = await integrations_service.is_gsc_connected(db, site_id=site_id)
    if not connected:
        return []
    return []


async def _fetch_yandex_links(db: AsyncSession, *, site_id: int) -> List[Tuple[str, str, Optional[str], Optional[str]]]:
    connected = await integrations_service.is_yandex_connected(db, site_id=site_id)
    if not connected:
        return []
    return []


async def _fetch_ahrefs_links(db: AsyncSession, *, site: Site, limit: int = 200) -> Dict[str, Any]:
    creds = await integrations_service.get_ahrefs_credentials(db, site_id=site.id)
    if not creds.get("connected"):
        return {"ok": False, "detail": "Ahrefs not connected", "items": []}
    target = f"{(site.domain or '').strip('/')}/"
    payload = await ahrefs_service.refdomains(api_key=str(creds.get("api_key") or ""), target=target, limit=limit, history="live")
    if not payload.get("ok"):
        return {
            "ok": False,
            "detail": payload.get("detail") or "Ahrefs error",
            "http_status": payload.get("http_status"),
            "body_preview": payload.get("body_preview"),
            "items": [],
        }
    raw_items = payload.get("items") or []
    items: List[Tuple[str, str, Optional[str], Optional[str], Optional[int], bool]] = []
    target_url = f"https://{site.domain}/"
    for it in raw_items:
        if not isinstance(it, dict):
            continue
        donor_domain = (it.get("domain") or "").strip().lower()
        if not donor_domain:
            continue
        source_url = donor_domain if donor_domain.startswith(("http://", "https://")) else f"https://{donor_domain}/"
        dr_raw = it.get("domain_rating")
        dr_val: Optional[int] = None
        if dr_raw is not None:
            try:
                dr_val = int(float(dr_raw))
            except Exception:
                dr_val = None
        dofollow_links = it.get("dofollow_links")
        lt = "dofollow"
        try:
            if dofollow_links is not None and int(dofollow_links) <= 0:
                lt = "nofollow"
        except Exception:
            pass
        is_spam = bool(it.get("is_spam"))
        items.append((source_url, target_url, None, lt, dr_val, is_spam))
    return {"ok": True, "items": items}


@router.get("")
async def list_links(
    site_id: int = Query(...),
    source: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    link_type: Optional[str] = Query(default=None),
    toxic: Optional[str] = Query(default=None),
    compare: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=500),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    cmp_norm = compare.upper() if compare else None
    if cmp_norm not in (None, "NEW", "LOST", "OK"):
        cmp_norm = None
    lt = link_type.lower() if link_type else None
    if lt not in (None, "dofollow", "nofollow"):
        lt = None
    tox = toxic.lower() if toxic else None
    if tox not in (None, "safe", "suspicious", "toxic"):
        tox = None
    return await link_service.list(
        db,
        site_id=site_id,
        source=source,
        status=status,
        link_type=lt,
        toxic=tox,
        compare=cmp_norm,
        q=q,
        limit=limit,
    )


@router.get("/stats")
async def link_stats(site_id: int = Query(...), days: int = Query(default=30), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await link_service.stats(db, site_id=site_id, days=days)


@router.get("/anchors")
async def anchor_stats(site_id: int = Query(...), limit: int = Query(default=50), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    limit = max(5, min(200, int(limit)))
    rows = (await db.execute(select(Backlink.anchor).where(Backlink.site_id == site_id))).all()
    counts: Dict[str, int] = {}
    total = 0
    for (a,) in rows:
        if not a:
            continue
        key = str(a).strip()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
        total += 1
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    perc = [round((v / total) * 100.0, 2) if total else 0 for v in values]
    return {"site_id": site_id, "total": total, "items": [{"anchor": k, "count": v, "pct": p} for (k, v), p in zip(items, perc)], "labels": labels, "values": values}


@router.get("/ahrefs-history")
async def ahrefs_history(site_id: int = Query(...), limit: int = Query(default=200), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    limit = max(1, min(500, int(limit)))
    rows = (await db.execute(
        select(MetricHistory)
        .where(MetricHistory.site_id == site_id, MetricHistory.metric_type == "links_ahrefs")
        .order_by(MetricHistory.created_at.asc())
        .limit(limit)
    )).scalars().all()
    return {
        "site_id": site_id,
        "items": [{"created_at": r.created_at.isoformat(), "value": r.value_json} for r in rows],
        "labels": [r.created_at.isoformat() for r in rows],
        "avg_dr": [int((r.value_json or {}).get("avg_dr") or 0) for r in rows],
        "toxic_pct": [float((r.value_json or {}).get("toxic_pct") or 0) for r in rows],
    }


@router.get("/quality-history")
async def links_quality_history(site_id: int = Query(...), limit: int = Query(default=200), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    limit = max(1, min(500, int(limit)))
    rows = (
        await db.execute(
            select(MetricHistory)
            .where(MetricHistory.site_id == site_id, MetricHistory.metric_type == "links_quality")
            .order_by(MetricHistory.created_at.asc())
            .limit(limit)
        )
    ).scalars().all()

    if not rows:
        total = int(
            (
                await db.execute(select(func.count(Backlink.id)).where(Backlink.site_id == site_id))
            ).scalar()
            or 0
        )
        toxic_cnt = int(
            (
                await db.execute(
                    select(func.count(Backlink.id)).where(
                        Backlink.site_id == site_id, Backlink.toxic_flag.in_(("toxic", "suspicious"))
                    )
                )
            ).scalar()
            or 0
        )
        dr_values = (
            await db.execute(select(Backlink.domain_score).where(Backlink.site_id == site_id, Backlink.domain_score.is_not(None)))
        ).all()
        dr_nums = [int(v) for (v,) in dr_values if v is not None]
        avg_dr = int(round(sum(dr_nums) / max(1, len(dr_nums)))) if dr_nums else 0
        toxic_pct = round((toxic_cnt / max(1, total)) * 100.0, 2) if total else 0.0
        ts = utcnow().isoformat()
        return {
            "site_id": site_id,
            "items": [{"created_at": ts, "value": {"avg_dr": avg_dr, "toxic_pct": toxic_pct, "total": total}}],
            "labels": [ts],
            "avg_dr": [avg_dr],
            "toxic_pct": [toxic_pct],
        }

    return {
        "site_id": site_id,
        "items": [{"created_at": r.created_at.isoformat(), "value": r.value_json} for r in rows],
        "labels": [r.created_at.isoformat() for r in rows],
        "avg_dr": [int((r.value_json or {}).get("avg_dr") or 0) for r in rows],
        "toxic_pct": [float((r.value_json or {}).get("toxic_pct") or 0) for r in rows],
    }


@router.get("/top-pages")
async def top_pages(site_id: int = Query(...), limit: int = Query(default=20), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    limit = max(5, min(100, int(limit)))
    rows = (await db.execute(
        select(Backlink.target_url, func.count(Backlink.id))
        .where(Backlink.site_id == site_id)
        .group_by(Backlink.target_url)
        .order_by(func.count(Backlink.id).desc())
        .limit(limit)
    )).all()
    return {"site_id": site_id, "items": [{"target_url": u, "count": int(c)} for u, c in rows]}


@router.get("/broken")
async def broken_links(site_id: int = Query(...), limit: int = Query(default=200), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    limit = max(1, min(500, int(limit)))
    rows = (await db.execute(
        select(Backlink).where(Backlink.site_id == site_id, Backlink.status == "broken").order_by(Backlink.last_checked.desc()).limit(limit)
    )).scalars().all()
    return {
        "site_id": site_id,
        "items": [
            {
                "id": b.id,
                "source_url": b.source_url,
                "target_url": b.target_url,
                "http_status": b.http_status,
                "last_checked": b.last_checked.isoformat() if b.last_checked else None,
            }
            for b in rows
        ],
    }


@router.get("/anchor-suggestions")
async def anchor_suggestions(site_id: int = Query(...), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    anchors_rows = (await db.execute(select(Backlink.anchor).where(Backlink.site_id == site_id))).all()
    counts: Dict[str, int] = {}
    for (a,) in anchors_rows:
        if not a:
            continue
        k = str(a).strip()
        if not k:
            continue
        counts[k] = counts.get(k, 0) + 1
    top = [k for k, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]]
    suggestions = []
    suggestions.extend([site.domain, f"https://{site.domain}", f"{site.domain} официальный сайт"])
    for a in top:
        suggestions.append(a)
        if len(a) >= 4:
            suggestions.append(f"{a} отзывы")
            suggestions.append(f"{a} цена")
    uniq = []
    seen = set()
    for s in suggestions:
        s = str(s).strip()
        if not s or s.lower() in seen:
            continue
        seen.add(s.lower())
        uniq.append(s)
    return {"site_id": site_id, "suggestions": uniq[:30]}


@router.post("/refresh")
async def refresh_links(
    background: BackgroundTasks,
    site_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    task = Task(site_id=site_id, title=f"Обновление ссылок: {site.domain}", description=None, status="in_progress")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    db.add(
        AppLog(
            level="INFO",
            category="links",
            method="POST",
            path="/api/links/refresh",
            status_code=None,
            message=f"scheduled links refresh site_id={site_id} task_id={task.id}",
            created_at=utcnow(),
        )
    )
    await db.commit()

    if settings.TESTING:
        task.status = "done"
        db.add(task)
        db.add(
            AppLog(
                level="INFO",
                category="links",
                method=None,
                path=None,
                status_code=None,
                message=f"links refresh done (testing) site_id={site_id} task_id={task.id}",
                created_at=utcnow(),
            )
        )
        await db.commit()
        return {"ok": True, "scheduled": False, "site_id": site_id, "task_id": task.id}

    async def _job():
        async with AsyncSessionLocal() as job_db:
            now = utcnow()
            try:
                gsc_links = await _fetch_gsc_links(job_db, site_id=site_id)
                y_links = await _fetch_yandex_links(job_db, site_id=site_id)

                gsc_pairs: List[Tuple[str, str]] = []
                for source_url, target_url, anchor, lt in gsc_links:
                    await link_service.upsert(
                        job_db,
                        site_id=site_id,
                        source_url=source_url,
                        target_url=target_url,
                        anchor=anchor,
                        link_type=lt,
                        source="gsc",
                        now=now,
                    )
                    gsc_pairs.append((source_url, target_url))

                y_pairs: List[Tuple[str, str]] = []
                for source_url, target_url, anchor, lt in y_links:
                    await link_service.upsert(
                        job_db,
                        site_id=site_id,
                        source_url=source_url,
                        target_url=target_url,
                        anchor=anchor,
                        link_type=lt,
                        source="yandex",
                        now=now,
                    )
                    y_pairs.append((source_url, target_url))

                if gsc_links:
                    await link_service.mark_lost_missing_from_snapshot(job_db, site_id=site_id, source="gsc", present_pairs=gsc_pairs, now=now)
                if y_links:
                    await link_service.mark_lost_missing_from_snapshot(job_db, site_id=site_id, source="yandex", present_pairs=y_pairs, now=now)

                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "done"
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="INFO",
                        category="links",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"links refresh done site_id={site_id} task_id={task.id}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()
            except Exception as e:
                logger.exception(f"Link refresh failed site_id={site_id}: {e}")
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "todo"
                    t.description = "Ошибка обновления ссылок. Проверьте логи."
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="ERROR",
                        category="links",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"links refresh failed site_id={site_id} task_id={task.id}: {e}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()

    background.add_task(_job)
    return {"ok": True, "scheduled": True, "site_id": site_id, "task_id": task.id}


@router.post("/refresh-ahrefs")
async def refresh_links_ahrefs(
    background: BackgroundTasks,
    site_id: int = Query(...),
    limit: int = Query(default=200),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    creds = await integrations_service.get_ahrefs_credentials(db, site_id=site_id)
    if not creds.get("connected"):
        raise HTTPException(status_code=400, detail="Ahrefs not connected")

    limit = max(10, min(500, int(limit)))
    task = Task(site_id=site_id, title=f"Обновление из Ahrefs: {site.domain}", description=None, status="in_progress")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    db.add(
        AppLog(
            level="INFO",
            category="links",
            method="POST",
            path="/api/links/refresh-ahrefs",
            status_code=None,
            message=f"scheduled links ahrefs refresh site_id={site_id} task_id={task.id}",
            created_at=utcnow(),
        )
    )
    await db.commit()

    async def _job():
        async with AsyncSessionLocal() as job_db:
            now = utcnow()
            try:
                site_row = await job_db.get(Site, site_id)
                if not site_row:
                    raise RuntimeError("Site not found")
                fetched = await _fetch_ahrefs_links(job_db, site=site_row, limit=limit)
                if not fetched.get("ok"):
                    hs = fetched.get("http_status")
                    bp = (fetched.get("body_preview") or "").strip()
                    extra = ""
                    if hs is not None:
                        extra += f" (HTTP {hs})"
                    if bp:
                        extra += f" body={bp}"
                    raise RuntimeError(str(fetched.get("detail") or "Ahrefs fetch failed") + extra)
                rows = fetched.get("items") or []
                present_pairs: List[Tuple[str, str]] = []
                spam_count = 0
                dr_values: List[int] = []
                for source_url, target_url, anchor, lt, dr_val, is_spam in rows:
                    await link_service.upsert(
                        job_db,
                        site_id=site_id,
                        source_url=source_url,
                        target_url=target_url,
                        anchor=anchor,
                        link_type=lt,
                        domain_score=dr_val,
                        source="ahrefs",
                        now=now,
                    )
                    present_pairs.append((source_url, target_url))
                    if is_spam:
                        spam_count += 1
                    if dr_val is not None:
                        dr_values.append(int(dr_val))
                if rows:
                    await link_service.mark_lost_missing_from_snapshot(job_db, site_id=site_id, source="ahrefs", present_pairs=present_pairs, now=now)

                total = len(rows)
                avg_dr = int(round(sum(dr_values) / max(1, len(dr_values)))) if dr_values else 0
                toxic_pct = round((spam_count / max(1, total)) * 100.0, 2) if total else 0.0
                await metrics_service.save(
                    job_db,
                    site_id=site_id,
                    metric_type="links_ahrefs",
                    value={"avg_dr": avg_dr, "toxic_pct": toxic_pct, "total": total, "active": total, "lost": 0, "broken": 0, "source": "ahrefs_api"},
                )

                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "done"
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="INFO",
                        category="links",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"links ahrefs refresh done site_id={site_id} task_id={task.id} total={total} avg_dr={avg_dr}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()
            except Exception as e:
                logger.exception(f"Ahrefs link refresh failed site_id={site_id}: {e}")
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "todo"
                    t.description = "Ошибка обновления из Ahrefs. Скорее всего нет API-доступа на тарифе или ключ неверный. Проверьте настройки Ahrefs или отключите интеграцию."
                    job_db.add(t)
                msg = str(e)
                level = "ERROR"
                if "HTTP 401" in msg or "HTTP 402" in msg or "HTTP 403" in msg or "HTTP 429" in msg:
                    level = "WARNING"
                job_db.add(
                    AppLog(
                        level=level,
                        category="links",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"links ahrefs refresh failed site_id={site_id} task_id={task.id}: {msg}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()

    if settings.TESTING:
        await _job()
        return {"ok": True, "scheduled": False, "site_id": site_id, "task_id": task.id}
    background.add_task(_job)
    return {"ok": True, "scheduled": True, "site_id": site_id, "task_id": task.id}


@router.post("/analyze")
async def analyze_links(
    background: BackgroundTasks,
    site_id: int = Query(...),
    limit: int = Query(default=300),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    task = Task(site_id=site_id, title=f"Анализ ссылок: {site.domain}", description=None, status="in_progress")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    db.add(
        AppLog(
            level="INFO",
            category="links",
            method="POST",
            path="/api/links/analyze",
            status_code=None,
            message=f"scheduled links analyze site_id={site_id} task_id={task.id}",
            created_at=utcnow(),
        )
    )
    await db.commit()

    if settings.TESTING:
        task.status = "done"
        db.add(task)
        db.add(
            AppLog(
                level="INFO",
                category="links",
                method=None,
                path=None,
                status_code=None,
                message=f"links analyze done (testing) site_id={site_id} task_id={task.id}",
                created_at=utcnow(),
            )
        )
        await db.commit()
        return {"ok": True, "scheduled": False, "site_id": site_id, "task_id": task.id}

    async def _job():
        async with AsyncSessionLocal() as job_db:
            try:
                await link_analysis_service.analyze_site(job_db, site_id=site_id, limit=limit)
                total = int(
                    (
                        await job_db.execute(select(func.count(Backlink.id)).where(Backlink.site_id == site_id))
                    ).scalar()
                    or 0
                )
                toxic_cnt = int(
                    (
                        await job_db.execute(
                            select(func.count(Backlink.id)).where(
                                Backlink.site_id == site_id, Backlink.toxic_flag.in_(("toxic", "suspicious"))
                            )
                        )
                    ).scalar()
                    or 0
                )
                dr_values = (
                    await job_db.execute(select(Backlink.domain_score).where(Backlink.site_id == site_id, Backlink.domain_score.is_not(None)))
                ).all()
                dr_nums = [int(v) for (v,) in dr_values if v is not None]
                avg_dr = int(round(sum(dr_nums) / max(1, len(dr_nums)))) if dr_nums else 0
                toxic_pct = round((toxic_cnt / max(1, total)) * 100.0, 2) if total else 0.0
                job_db.add(
                    MetricHistory(
                        site_id=site_id,
                        metric_type="links_quality",
                        value={"avg_dr": avg_dr, "toxic_pct": toxic_pct, "total": total},
                        created_at=utcnow(),
                    )
                )
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "done"
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="INFO",
                        category="links",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"links analyze done site_id={site_id} task_id={task.id}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()
            except Exception as e:
                logger.exception(f"Link analyze failed site_id={site_id}: {e}")
                t = await job_db.get(Task, task.id)
                if t:
                    t.status = "todo"
                    t.description = "Ошибка анализа ссылок. Проверьте логи."
                    job_db.add(t)
                job_db.add(
                    AppLog(
                        level="ERROR",
                        category="links",
                        method=None,
                        path=None,
                        status_code=None,
                        message=f"links analyze failed site_id={site_id} task_id={task.id}: {e}",
                        created_at=utcnow(),
                    )
                )
                await job_db.commit()

    background.add_task(_job)
    return {"ok": True, "scheduled": True, "site_id": site_id, "task_id": task.id}


@router.get("/last-analyzed")
async def last_analyzed(site_id: int = Query(...), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    row = (
        await db.execute(
            select(MetricHistory)
            .where(
                MetricHistory.site_id == site_id,
                MetricHistory.metric_type.in_(("links_quality", "links_ahrefs")),
            )
            .order_by(MetricHistory.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if not row:
        return {"site_id": site_id, "last_analyzed_at": None, "value": None}
    return {"site_id": site_id, "last_analyzed_at": row.created_at.isoformat() if row.created_at else None, "value": row.value_json}


@router.post("/import-csv")
async def import_links_csv(
    site_id: int = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    content = await file.read()
    return await link_import_service.import_csv(db, site_id=site_id, content_bytes=content)


class LinksImportTextPayload(BaseModel):
    text: str


class LinkManualPayload(BaseModel):
    source_url: str
    target_url: str
    anchor: Optional[str] = None
    link_type: Optional[str] = None
    domain_score: Optional[int] = None


@router.post("/import-text")
async def import_links_text(
    payload: LinksImportTextPayload,
    site_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await link_import_service.import_text(db, site_id=site_id, text=payload.text)


@router.post("/add")
async def add_link_manual(
    payload: LinkManualPayload,
    site_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    row = await link_service.upsert(
        db,
        site_id=site_id,
        source_url=payload.source_url,
        target_url=payload.target_url,
        anchor=payload.anchor,
        link_type=payload.link_type,
        domain_score=payload.domain_score,
        source="manual",
    )
    return {"ok": True, "id": int(row.id)}


@router.post("/clear")
async def clear_links(
    request: Request,
    site_id: int = Query(...),
    mode: str = Query(default="all"),
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

    m = (mode or "all").strip().lower()
    stmt_where = (Backlink.site_id == int(site_id))
    if m == "import":
        stmt_where = stmt_where & (Backlink.source == "import")
    elif m == "manual":
        stmt_where = stmt_where & (Backlink.source == "manual")
    elif m == "gsc":
        stmt_where = stmt_where & (Backlink.source == "gsc")
    elif m == "yandex":
        stmt_where = stmt_where & (Backlink.source == "yandex")
    elif m == "ahrefs":
        stmt_where = stmt_where & (Backlink.source == "ahrefs")
    elif m == "purchased":
        stmt_where = stmt_where & (Backlink.source == "purchased")
    elif m != "all":
        raise HTTPException(status_code=400, detail="Invalid mode")

    ids_subq = select(Backlink.id).where(stmt_where)
    await db.execute(delete(BacklinkStatusHistory).where(BacklinkStatusHistory.backlink_id.in_(ids_subq)))
    res = await db.execute(delete(Backlink).where(stmt_where))
    await db.commit()
    return {"ok": True, "deleted": int(res.rowcount or 0), "site_id": int(site_id), "mode": m}
