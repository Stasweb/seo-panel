from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.competitor_service import competitor_service
from app.services.competitor_backlink_service import competitor_backlink_service
from app.services.ai_runtime_service import ai_runtime_service
from app.services.ai_service import ai_service
from app.core.database import get_db
from app.services.organization_service import organization_service
from app.models.models import Task, Competitor, CompetitorSnapshot, Site
from sqlalchemy import select
from pydantic import BaseModel
import json
import re
from app.utils.time import utcnow


router = APIRouter(prefix="/competitors", tags=["competitors"])

def _norm_domain(value: str) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = s.split("/")[0]
    if s.startswith("www."):
        s = s[4:]
    return s


class CompetitorCreatePayload(BaseModel):
    domain: str
    site_id: Optional[int] = None
    label: Optional[str] = None


@router.get("/analyze")
async def analyze_competitor(domain: str = Query(...), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    payload = await competitor_service.analyze(domain=domain)
    if not payload.get("ok"):
        return payload
    resolved = await ai_runtime_service.resolve(db)
    if resolved.get("effective_provider") == "ollama" and resolved.get("effective_model"):
        context = {
            "domain": payload.get("domain"),
            "url": payload.get("url"),
            "http_status": payload.get("http_status"),
            "title": payload.get("title"),
            "h1": payload.get("h1"),
            "meta_description": payload.get("meta_description"),
            "canonical": payload.get("canonical"),
            "robots": payload.get("robots"),
            "sitemap": payload.get("sitemap"),
            "structure": payload.get("structure"),
        }
        improved = await ai_service.enhance_competitor_issues_ai(
            context=context,
            issues=list(payload.get("issues") or []),
            model=str(resolved["effective_model"]),
        )
        if improved is not None:
            payload["issues"] = improved
            payload["ai_used"] = True
            payload["ai_model"] = str(resolved["effective_model"])
    return payload


@router.get("/saved")
async def list_saved_competitors(
    request: Request,
    site_id: int | None = Query(default=None),
    limit: int = Query(default=200),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    limit = max(1, min(500, int(limit)))
    stmt = select(Competitor, Site.domain).outerjoin(Site, Competitor.site_id == Site.id).where(Competitor.organization_id == int(org_id))
    if site_id is not None:
        stmt = stmt.where(Competitor.site_id == int(site_id))
    stmt = stmt.order_by(Competitor.last_checked_at.desc().nullslast(), Competitor.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).all()
    items = []
    for c, site_domain in rows:
        items.append(
            {
                "id": int(c.id),
                "domain": c.domain,
                "label": c.label,
                "site_id": c.site_id,
                "site_domain": str(site_domain or "") if c.site_id else "",
                "last_checked_at": c.last_checked_at.isoformat() if c.last_checked_at else None,
                "last_http_status": c.last_http_status,
                "backlinks_total": c.backlinks_total,
                "donors_total": c.donors_total,
                "dofollow_pct": c.dofollow_pct,
                "avg_dr": c.avg_dr,
                "gap_donors": c.gap_donors,
                "overlap_donors": c.overlap_donors,
            }
        )
    return {"ok": True, "items": items}


@router.post("/saved")
async def create_saved_competitor(
    payload: CompetitorCreatePayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    dom = _norm_domain(payload.domain)
    if not dom:
        raise HTTPException(status_code=400, detail="domain is required")
    if payload.site_id is not None:
        site = await db.get(Site, int(payload.site_id))
        if not site:
            raise HTTPException(status_code=400, detail="Invalid site_id")
        if site.organization_id != int(org_id):
            site.organization_id = int(org_id)
            db.add(site)
            await db.commit()

    existing = (await db.execute(select(Competitor).where(Competitor.organization_id == int(org_id), Competitor.domain == dom))).scalars().first()
    if existing:
        if payload.site_id is not None and existing.site_id is None:
            existing.site_id = int(payload.site_id)
        if payload.label is not None and (payload.label or "").strip():
            existing.label = (payload.label or "").strip()[:255]
        db.add(existing)
        await db.commit()
        return {"ok": True, "id": int(existing.id), "created": False}

    row = Competitor(
        organization_id=int(org_id),
        site_id=int(payload.site_id) if payload.site_id is not None else None,
        domain=dom,
        label=(payload.label or "").strip()[:255] or None,
        created_at=utcnow(),
    )
    db.add(row)
    await db.commit()
    return {"ok": True, "id": int(row.id), "created": True}


@router.delete("/saved/{competitor_id}")
async def delete_saved_competitor(
    competitor_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    row = (await db.execute(select(Competitor).where(Competitor.id == int(competitor_id), Competitor.organization_id == int(org_id)))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.post("/saved/{competitor_id}/refresh")
async def refresh_saved_competitor(
    competitor_id: int,
    request: Request,
    site_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    row = (await db.execute(select(Competitor).where(Competitor.id == int(competitor_id), Competitor.organization_id == int(org_id)))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    used_site_id = int(site_id) if site_id is not None else (int(row.site_id) if row.site_id is not None else None)
    if used_site_id is not None:
        site = await db.get(Site, int(used_site_id))
        if not site:
            used_site_id = None
        elif site.organization_id != int(org_id):
            site.organization_id = int(org_id)
            db.add(site)
            await db.commit()

    analysis = await competitor_service.analyze(domain=row.domain)
    stats = await competitor_backlink_service.stats(
        db,
        organization_id=int(org_id),
        competitor_domain=row.domain,
        limit=50,
        site_id=used_site_id,
    )
    combined = {"analysis": analysis, "links": stats}

    row.last_checked_at = utcnow()
    row.last_http_status = analysis.get("http_status") if isinstance(analysis, dict) else None
    row.last_title = (analysis.get("title") if isinstance(analysis, dict) else None) or None
    row.backlinks_total = int(stats.get("total") or 0) if isinstance(stats, dict) else None
    row.donors_total = int(stats.get("donors_total") or 0) if isinstance(stats, dict) else None
    try:
        row.dofollow_pct = float(stats.get("dofollow_pct")) if stats.get("dofollow_pct") is not None else None
    except Exception:
        row.dofollow_pct = None
    row.avg_dr = int(stats.get("avg_dr") or 0) if isinstance(stats, dict) else None
    ov = (stats.get("overlap") if isinstance(stats, dict) else None) or None
    gap = (stats.get("gap") if isinstance(stats, dict) else None) or None
    row.overlap_donors = int(ov.get("overlap_count") or 0) if isinstance(ov, dict) else None
    row.gap_donors = int(gap.get("donor_gap_count") or 0) if isinstance(gap, dict) else None
    row.last_snapshot_json = json.dumps(combined, ensure_ascii=False)
    db.add(row)
    await db.flush()

    snap = CompetitorSnapshot(
        competitor_id=int(row.id),
        created_at=utcnow(),
        http_status=row.last_http_status,
        backlinks_total=row.backlinks_total,
        donors_total=row.donors_total,
        dofollow_pct=row.dofollow_pct,
        avg_dr=row.avg_dr,
        gap_donors=row.gap_donors,
        overlap_donors=row.overlap_donors,
        snapshot_json=row.last_snapshot_json,
    )
    db.add(snap)
    await db.commit()
    return {"ok": True, "id": int(row.id), "snapshot_id": int(snap.id), "analysis": analysis, "links": stats}


@router.get("/saved/{competitor_id}/history")
async def saved_competitor_history(
    competitor_id: int,
    request: Request,
    limit: int = Query(default=30),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    limit = max(1, min(200, int(limit)))
    row = (await db.execute(select(Competitor).where(Competitor.id == int(competitor_id), Competitor.organization_id == int(org_id)))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    snaps = (
        await db.execute(
            select(CompetitorSnapshot)
            .where(CompetitorSnapshot.competitor_id == int(row.id))
            .order_by(CompetitorSnapshot.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    items = []
    for s in snaps:
        items.append(
            {
                "id": int(s.id),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "http_status": s.http_status,
                "backlinks_total": s.backlinks_total,
                "donors_total": s.donors_total,
                "dofollow_pct": s.dofollow_pct,
                "avg_dr": s.avg_dr,
                "gap_donors": s.gap_donors,
                "overlap_donors": s.overlap_donors,
            }
        )
    return {"ok": True, "competitor": {"id": int(row.id), "domain": row.domain, "label": row.label, "site_id": row.site_id}, "items": items}


@router.post("/backlinks/import")
async def import_competitor_backlinks(
    request: Request,
    domain: str = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    content = await file.read()
    return await competitor_backlink_service.import_csv(db, organization_id=int(org_id), competitor_domain=domain, content_bytes=content)


@router.get("/backlinks/stats")
async def competitor_backlinks_stats(
    request: Request,
    domain: str = Query(...),
    site_id: int | None = Query(default=None),
    limit: int = Query(default=50),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    return await competitor_backlink_service.stats(
        db,
        organization_id=int(org_id),
        competitor_domain=domain,
        limit=limit,
        site_id=int(site_id) if site_id is not None else None,
    )


@router.post("/backlinks/clear")
async def clear_competitor_backlinks(
    request: Request,
    domain: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    deleted = await competitor_backlink_service.clear(db, organization_id=int(org_id), competitor_domain=domain)
    return {"ok": True, "deleted": deleted}


@router.get("/backlinks/gap/export")
async def export_competitor_gap_csv(
    request: Request,
    domain: str = Query(...),
    site_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    payload = await competitor_backlink_service.stats(
        db,
        organization_id=int(org_id),
        competitor_domain=domain,
        limit=200,
        site_id=int(site_id),
    )
    gap = payload.get("gap") or {}
    donors = gap.get("donor_gap") or []
    return {"ok": True, "domain": domain, "site_id": int(site_id), "items": donors}


@router.post("/backlinks/gap/create-tasks")
async def create_tasks_for_competitor_gap(
    request: Request,
    domain: str = Query(...),
    site_id: int = Query(...),
    limit: int = Query(default=30),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id

    limit = max(1, min(200, int(limit)))
    payload = await competitor_backlink_service.stats(
        db,
        organization_id=int(org_id),
        competitor_domain=domain,
        limit=200,
        site_id=int(site_id),
    )
    gap = payload.get("gap") or {}
    donors = list(gap.get("donor_gap") or [])[:limit]
    if not donors:
        return {"ok": True, "created": 0, "skipped_duplicates": 0, "task_ids": []}

    titles = [f"Линкбилдинг: получить ссылку с {d}" for d in donors]
    existing = (await db.execute(select(Task.title).where(Task.site_id == int(site_id), Task.status != "done", Task.title.in_(titles)))).scalars().all()
    existing_set = {str(x) for x in existing}

    created_ids = []
    skipped = 0
    for donor in donors:
        t = f"Линкбилдинг: получить ссылку с {donor}"
        if t in existing_set:
            skipped += 1
            continue
        row = Task(
            site_id=int(site_id),
            title=t,
            description=f"Конкурент: {domain}\nДонор есть у конкурента, но отсутствует у нас.\nДействие: найти страницу/размещение/анкор и получить ссылку.",
            status="todo",
            priority="normal",
            source_url=None,
            deep_audit_report_id=None,
        )
        db.add(row)
        await db.flush()
        created_ids.append(int(row.id))
    await db.commit()
    return {"ok": True, "created": len(created_ids), "skipped_duplicates": int(skipped), "task_ids": created_ids}


@router.get("/backlinks/donor")
async def competitor_donor_details(
    request: Request,
    domain: str = Query(...),
    donor: str = Query(...),
    limit: int = Query(default=200),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    return await competitor_backlink_service.donor_details(
        db,
        organization_id=int(org_id),
        competitor_domain=domain,
        donor_domain=donor,
        limit=limit,
    )


@router.post("/backlinks/donor/create-task")
async def create_task_for_competitor_donor(
    request: Request,
    domain: str = Query(...),
    site_id: int = Query(...),
    donor: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    title = f"Линкбилдинг: получить ссылку с {donor}"
    existing = (
        await db.execute(select(Task.title).where(Task.site_id == int(site_id), Task.status != "done", Task.title == title))
    ).scalars().first()
    if existing:
        return {"ok": True, "created": 0, "skipped_duplicates": 1, "task_ids": []}
    row = Task(
        site_id=int(site_id),
        title=title,
        description=f"Конкурент: {domain}\nДонор: {donor}\nДействие: найти страницу/размещение/анкор и получить ссылку.",
        status="todo",
        priority="normal",
        source_url=None,
        deep_audit_report_id=None,
    )
    db.add(row)
    await db.commit()
    return {"ok": True, "created": 1, "skipped_duplicates": 0, "task_ids": [int(row.id)]}
