from fastapi import APIRouter, Depends, Query, Request
from app.services.seo_service import seo_service
from app.schemas.schemas import DensityRequest, MetaRequest, AuditRequest, AuditResult, DeepAuditRequest, DeepAuditResult
from typing import Any, Dict
from app.core.config import settings
from app.utils.user_agents import resolve_user_agent
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.ai_runtime_service import ai_runtime_service
from app.services.ai_service import ai_service
from app.models.models import DeepAuditReport, Site
from app.models.models import Task
from app.services.organization_service import organization_service
from sqlalchemy import select, delete
import json
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import HTTPException

router = APIRouter(prefix="/seo", tags=["seo"])

@router.post("/density")
async def keyword_density(payload: DensityRequest) -> Dict[str, Any]:
    """
    Calculate keyword density.
    """
    density = seo_service.calculate_keyword_density(payload.text)
    return {"density": density}

@router.post("/meta")
async def generate_meta(payload: MetaRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Generate meta description.
    """
    resolved = await ai_runtime_service.resolve(db)
    if resolved.get("effective_provider") == "ollama" and resolved.get("effective_model"):
        out = await ai_service.generate_meta_ai(payload.content, max_length=payload.max_length, model=str(resolved["effective_model"]))
        if out is not None:
            return {"meta": out.get("meta") or "", "length": int(out.get("length") or 0)}
    meta = seo_service.generate_meta_description(payload.content, max_length=payload.max_length)
    return {"meta": meta, "length": len(meta)}

@router.post("/audit", response_model=AuditResult)
async def audit_url(payload: AuditRequest, db: AsyncSession = Depends(get_db)):
    """
    Quick audit for a single URL.
    """
    ua = resolve_user_agent(payload.ua, payload.custom_ua, settings.USER_AGENT)
    result = await seo_service.check_url(payload.url, user_agent=ua, user_agent_choice=payload.ua, custom_user_agent=payload.custom_ua)
    resolved = await ai_runtime_service.resolve(db)
    if resolved.get("effective_provider") == "ollama" and resolved.get("effective_model"):
        audit_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
        explained = await ai_service.explain_audit_ai(audit=audit_dict, model=str(resolved["effective_model"]))
        if explained is not None:
            return AuditResult(
                **audit_dict,
                ai_used=True,
                ai_model=str(resolved["effective_model"]),
                ai_summary=str(explained.get("summary") or ""),
                ai_actions=list(explained.get("actions") or []),
            )
    return result


@router.post("/deep-audit", response_model=DeepAuditResult)
async def deep_audit_url(payload: DeepAuditRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await seo_service.deep_audit_url(
        payload.url,
        user_agent_choice=payload.ua,
        custom_user_agent=payload.custom_ua,
        suggest_mode=payload.suggest_mode,
        suggest_variants=payload.suggest_variants,
        target_keyword=payload.target_keyword,
    )
    resolved = await ai_runtime_service.resolve(db)
    if resolved.get("effective_provider") == "ollama" and resolved.get("effective_model"):
        explained = await ai_service.explain_deep_audit_ai(audit=result, model=str(resolved["effective_model"]))
        if explained is not None:
            result["ai_used"] = True
            result["ai_model"] = str(resolved["effective_model"])
            result["ai_summary"] = str(explained.get("summary") or "")
            result["ai_actions"] = list(explained.get("actions") or [])

    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id

    final_url = (result.get("final_url") or result.get("url") or payload.url or "").strip() or None
    site_id = None
    try:
        parsed = urlparse(final_url or "")
        host = (parsed.netloc or "").strip().lower()
        if host.startswith("www."):
            host = host[4:]
        if host:
            s = (await db.execute(select(Site).where(Site.domain == host, Site.organization_id == org_id))).scalars().first()
            if s:
                site_id = int(s.id)
    except Exception:
        site_id = None

    row = DeepAuditReport(
        organization_id=org_id,
        site_id=site_id,
        url=str(payload.url),
        final_url=str(final_url) if final_url else None,
        status_code=result.get("status_code"),
        response_time_ms=result.get("response_time_ms"),
        title=result.get("title"),
        meta_description=result.get("meta_description"),
        h1=result.get("h1"),
        canonical=result.get("canonical"),
        robots_meta=result.get("robots_meta"),
        x_robots_tag=result.get("x_robots_tag"),
        word_count=result.get("word_count"),
        links_internal=result.get("links_internal"),
        links_external=result.get("links_external"),
        images_missing_alt=result.get("images_missing_alt"),
        spam_score=result.get("spam_score"),
        indexable=result.get("indexable"),
        is_indexed=result.get("is_indexed"),
        target_keyword=(payload.target_keyword or "").strip() or None,
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    await db.commit()

    if final_url:
        ids = (
            await db.execute(
                select(DeepAuditReport.id)
                .where(DeepAuditReport.organization_id == org_id, DeepAuditReport.final_url == final_url)
                .order_by(DeepAuditReport.created_at.desc())
                .offset(30)
            )
        ).scalars().all()
        if ids:
            await db.execute(delete(DeepAuditReport).where(DeepAuditReport.id.in_(list(ids))))
            await db.commit()
    return DeepAuditResult(**result)


@router.get("/deep-audit/history")
async def deep_audit_history(
    request: Request,
    url: str = Query(..., min_length=1),
    limit: int = Query(default=10),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    limit = max(1, min(50, int(limit)))
    u = (url or "").strip()
    stmt = (
        select(DeepAuditReport)
        .where(DeepAuditReport.organization_id == org_id, DeepAuditReport.final_url == u)
        .order_by(DeepAuditReport.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    items = []
    for r in rows:
        items.append(
            {
                "id": int(r.id),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "status_code": r.status_code,
                "response_time_ms": r.response_time_ms,
                "indexable": r.indexable,
                "is_indexed": r.is_indexed,
                "spam_score": r.spam_score,
                "images_missing_alt": r.images_missing_alt,
                "links_internal": r.links_internal,
                "links_external": r.links_external,
                "word_count": r.word_count,
                "title": r.title,
                "meta_description": r.meta_description,
                "canonical": r.canonical,
            }
        )
    return {"url": u, "items": items}


@router.get("/deep-audit/diff")
async def deep_audit_diff(
    request: Request,
    url: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    u = (url or "").strip()
    stmt = (
        select(DeepAuditReport)
        .where(DeepAuditReport.organization_id == org_id, DeepAuditReport.final_url == u)
        .order_by(DeepAuditReport.created_at.desc())
        .limit(2)
    )
    rows = (await db.execute(stmt)).scalars().all()
    if len(rows) < 2:
        return {"url": u, "current": None, "previous": None, "diff": {}}
    cur, prev = rows[0], rows[1]
    fields = [
        "status_code",
        "response_time_ms",
        "indexable",
        "is_indexed",
        "spam_score",
        "images_missing_alt",
        "links_internal",
        "links_external",
        "word_count",
        "title",
        "meta_description",
        "canonical",
    ]
    diff: Dict[str, Any] = {}
    for f in fields:
        a = getattr(prev, f)
        b = getattr(cur, f)
        if a != b:
            entry: Dict[str, Any] = {"from": a, "to": b}
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                entry["delta"] = b - a
            diff[f] = entry
    return {
        "url": u,
        "current": {"id": int(cur.id), "created_at": cur.created_at.isoformat() if cur.created_at else None},
        "previous": {"id": int(prev.id), "created_at": prev.created_at.isoformat() if prev.created_at else None},
        "diff": diff,
    }


@router.get("/deep-audit/report/{report_id}")
async def deep_audit_report(
    report_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id

    row = (
        await db.execute(
            select(DeepAuditReport).where(DeepAuditReport.id == int(report_id), DeepAuditReport.organization_id == org_id)
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        data = json.loads(row.result_json or "{}")
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    return {
        "id": int(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "final_url": row.final_url,
        "result": data,
    }


@router.get("/deep-audit/latest")
async def deep_audit_latest(
    request: Request,
    url: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    u = (url or "").strip()
    row = (
        await db.execute(
            select(DeepAuditReport)
            .where(DeepAuditReport.organization_id == org_id, DeepAuditReport.final_url == u)
            .order_by(DeepAuditReport.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        data = json.loads(row.result_json or "{}")
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    return {
        "id": int(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "final_url": row.final_url,
        "result": data,
    }


class DeepAuditCreateTasksRequest(BaseModel):
    url: str


@router.post("/deep-audit/create-tasks")
async def deep_audit_create_tasks(
    payload: DeepAuditCreateTasksRequest,
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

    u = (payload.url or "").strip()
    if not u:
        raise HTTPException(status_code=400, detail="url is required")

    stmt = (
        select(DeepAuditReport)
        .where(DeepAuditReport.organization_id == org_id, DeepAuditReport.final_url == u)
        .order_by(DeepAuditReport.created_at.desc())
        .limit(1)
    )
    report = (await db.execute(stmt)).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Deep audit report not found for this url")
    if not report.site_id:
        raise HTTPException(status_code=400, detail="Cannot create tasks: site is not detected for this url")

    try:
        data = json.loads(report.result_json or "{}")
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    tasks = _audit_to_tasks(data)
    if not tasks:
        return {"ok": True, "created": 0, "skipped_duplicates": 0, "site_id": int(report.site_id), "task_ids": []}

    titles = [t["title"] for t in tasks]
    existing = (
        await db.execute(
            select(Task.title)
            .where(Task.site_id == int(report.site_id), Task.status != "done", Task.title.in_(titles))
        )
    ).scalars().all()
    existing_titles = {str(x) for x in existing}

    created_ids = []
    skipped = 0
    for t in tasks:
        if t["title"] in existing_titles:
            skipped += 1
            continue
        row = Task(
            site_id=int(report.site_id),
            title=t["title"],
            description=t.get("description") or None,
            status="todo",
            priority=t.get("priority") or "normal",
            source_url=str(report.final_url or report.url or u),
            deep_audit_report_id=int(report.id),
        )
        db.add(row)
        await db.flush()
        created_ids.append(int(row.id))
    await db.commit()

    return {
        "ok": True,
        "created": len(created_ids),
        "skipped_duplicates": int(skipped),
        "site_id": int(report.site_id),
        "task_ids": created_ids,
    }


def _audit_to_tasks(audit: Dict[str, Any]) -> list[Dict[str, Any]]:
    url = str(audit.get("final_url") or audit.get("url") or "").strip()
    title = str(audit.get("title") or "").strip()
    meta = str(audit.get("meta_description") or "").strip()
    h1 = str(audit.get("h1") or "").strip()

    tasks: list[Dict[str, Any]] = []

    def add(title_txt: str, desc: str, priority: str = "normal") -> None:
        tasks.append({"title": f"Аудит: {title_txt}", "description": desc, "priority": priority})

    indexable = audit.get("indexable")
    reasons = audit.get("indexability_reasons") or []
    if indexable is False:
        add(
            "Сделать страницу indexable",
            f"URL: {url}\nПричины: {', '.join([str(r) for r in reasons])}",
            "high",
        )

    if audit.get("robots_meta") and "noindex" in str(audit.get("robots_meta") or "").lower():
        add("Убрать noindex в meta robots", f"URL: {url}\nrobots_meta: {audit.get('robots_meta')}", "high")
    if audit.get("x_robots_tag") and "noindex" in str(audit.get("x_robots_tag") or "").lower():
        add("Убрать noindex в X-Robots-Tag", f"URL: {url}\nX-Robots-Tag: {audit.get('x_robots_tag')}", "high")

    canonical = str(audit.get("canonical") or "").strip()
    if not canonical:
        add("Проверить/добавить canonical", f"URL: {url}\ncanonical отсутствует", "normal")

    if not title:
        add("Добавить Title", f"URL: {url}\nTitle отсутствует", "high")
    elif len(title) > 75:
        add("Сократить Title", f"URL: {url}\nTitle: {title}\nДлина: {len(title)}", "normal")

    if not h1:
        add("Добавить H1", f"URL: {url}\nH1 отсутствует", "high")

    if not meta:
        add("Добавить meta description", f"URL: {url}\nmeta description отсутствует", "normal")
    elif len(meta) > 180:
        add("Сократить meta description", f"URL: {url}\nДлина: {len(meta)}", "low")

    spam_score = int(audit.get("spam_score") or 0)
    if spam_score >= 60:
        flags = audit.get("spam_flags") or []
        add(
            "Убрать признаки SEO-спама",
            f"URL: {url}\nSPAM score: {spam_score}\nФлаги: {', '.join([str(x) for x in flags])}",
            "high",
        )
    elif spam_score >= 30:
        flags = audit.get("spam_flags") or []
        add(
            "Снизить риск SEO-спама",
            f"URL: {url}\nSPAM score: {spam_score}\nФлаги: {', '.join([str(x) for x in flags])}",
            "normal",
        )

    images_missing_alt = audit.get("images_missing_alt")
    if isinstance(images_missing_alt, int) and images_missing_alt > 0:
        add("Добавить alt у изображений", f"URL: {url}\nКартинок без alt: {images_missing_alt}", "normal")

    rt = audit.get("response_time_ms")
    if isinstance(rt, int) and rt >= 1500:
        add("Ускорить загрузку страницы", f"URL: {url}\nВремя ответа: {rt} ms", "normal")

    wc = audit.get("word_count")
    if isinstance(wc, int) and wc > 0 and wc < 250:
        add("Расширить контент", f"URL: {url}\nСлов на странице: {wc}", "low")

    tks = audit.get("target_keyword_stats") or {}
    if isinstance(tks, dict) and tks.get("is_spam"):
        add(
            "Снизить спам по целевому ключу",
            f"URL: {url}\nКлюч: {tks.get('keyword')}\nПлотность: {tks.get('density_pct')}%\nФлаги: {', '.join([str(x) for x in (tks.get('spam_flags') or [])])}",
            "high" if spam_score >= 60 else "normal",
        )

    ai_actions = audit.get("ai_actions") or []
    if isinstance(ai_actions, list) and ai_actions:
        for a in ai_actions[:6]:
            s = str(a).strip()
            if not s:
                continue
            add(f"ИИ: {s[:60]}", f"URL: {url}\nДействие ИИ: {s}", "normal")

    uniq: Dict[str, Dict[str, Any]] = {}
    for t in tasks:
        uniq[t["title"]] = t
    return list(uniq.values())[:12]
