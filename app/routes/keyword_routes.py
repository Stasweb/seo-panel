from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import KeywordMetrics, Site
from app.utils.time import utcnow
from app.services.keyword_suggest_service import keyword_suggest_service


router = APIRouter(prefix="/keywords", tags=["keywords"])


class KeywordCreateRequest(BaseModel):
    site_id: int
    keyword: str
    position: Optional[float] = None
    url: Optional[str] = None
    frequency: Optional[int] = None
    source: str = "manual"


@router.get("/suggest")
async def keyword_suggest(
    query: str = Query(..., min_length=1),
    engines: Optional[str] = Query(default="google,yandex,bing,ddg"),
    lang: str = Query(default="ru"),
    mode: str = Query(default="basic"),
    max_variants: int = Query(default=30),
    max_per_engine: int = Query(default=30),
) -> Dict[str, Any]:
    eng = [e.strip().lower() for e in (engines or "").split(",") if e and e.strip()]
    payload = await keyword_suggest_service.suggest(
        query,
        engines=eng,
        lang=(lang or "ru"),
        mode=mode,
        max_variants=max_variants,
        max_per_engine=max_per_engine,
    )
    return payload


@router.get("")
async def list_keywords(
    site_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=300),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    limit = max(1, min(2000, int(limit)))
    stmt = select(KeywordMetrics).order_by(KeywordMetrics.created_at.desc()).limit(limit)
    if site_id is not None:
        stmt = stmt.where(KeywordMetrics.site_id == site_id)
    if q:
        qv = f"%{q.strip()}%"
        stmt = stmt.where((KeywordMetrics.keyword.ilike(qv)) | (KeywordMetrics.landing_url.ilike(qv)))
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "site_id": r.site_id,
            "keyword": r.keyword,
            "position": r.position,
            "url": r.landing_url,
            "frequency": r.frequency,
            "source": r.source,
            "date": r.date.isoformat() if r.date else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("")
async def create_keyword(payload: KeywordCreateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, payload.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    kw = (payload.keyword or "").strip()
    if not kw:
        raise HTTPException(status_code=400, detail="keyword required")
    row = KeywordMetrics(
        site_id=payload.site_id,
        keyword=kw,
        position=payload.position,
        landing_url=(payload.url or None),
        frequency=payload.frequency,
        source=(payload.source or "manual"),
        date=date.today(),
        created_at=utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"ok": True, "id": row.id}

@router.post("/import-csv")
async def import_keywords_csv(site_id: int = Query(...), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    raw = await file.read()
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = str(raw)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Empty CSV")

    imported = 0
    errors: List[str] = []
    for i, row in enumerate(reader, start=2):
        try:
            kw = (row.get("keyword") or row.get("Keyword") or row.get("query") or row.get("Query") or "").strip()
            if not kw:
                continue
            pos_raw = (row.get("position") or row.get("Position") or "").strip()
            url = (row.get("url") or row.get("URL") or row.get("landing_url") or row.get("Landing URL") or "").strip() or None
            freq_raw = (row.get("frequency") or row.get("Frequency") or "").strip()
            position = float(pos_raw) if pos_raw else None
            frequency = int(float(freq_raw)) if freq_raw else None

            db.add(
                KeywordMetrics(
                    site_id=site_id,
                    keyword=kw,
                    position=position,
                    landing_url=url,
                    frequency=frequency,
                    source="csv",
                    date=date.today(),
                    created_at=utcnow(),
                )
            )
            imported += 1
        except Exception as e:
            errors.append(f"line {i}: {e}")
            continue

    await db.commit()
    return {"ok": True, "imported": imported, "errors": errors[:20]}


@router.delete("/{keyword_id}")
async def delete_keyword(keyword_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    row = await db.get(KeywordMetrics, keyword_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.get("/history")
async def keywords_history(
    site_id: int = Query(...),
    keyword: Optional[str] = Query(default=None),
    days: int = Query(default=30),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    days = max(7, min(365, int(days)))
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    stmt = (
        select(KeywordMetrics.date.label("d"), func.avg(KeywordMetrics.position).label("avg_pos"))
        .where(KeywordMetrics.site_id == site_id, KeywordMetrics.position.is_not(None))
        .group_by(KeywordMetrics.date)
        .order_by(KeywordMetrics.date.asc())
    )
    if keyword:
        stmt = stmt.where(KeywordMetrics.keyword == keyword.strip())

    rows = (await db.execute(stmt)).all()
    labels = [r.d.isoformat() if r.d else "" for r in rows][-days:]
    values = [round(float(r.avg_pos or 0), 2) for r in rows][-days:]
    return {"site_id": site_id, "keyword": keyword, "labels": labels, "values": values, "label": "Средняя позиция", "reverse_y": True}


@router.get("/cannibalization")
async def cannibalization(site_id: int = Query(...), limit: int = Query(default=50), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    limit = max(5, min(200, int(limit)))
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    stmt = (
        select(KeywordMetrics.keyword, func.count(func.distinct(KeywordMetrics.landing_url)).label("urls"))
        .where(KeywordMetrics.site_id == site_id, KeywordMetrics.landing_url.is_not(None))
        .group_by(KeywordMetrics.keyword)
        .having(func.count(func.distinct(KeywordMetrics.landing_url)) >= 2)
        .order_by(func.count(func.distinct(KeywordMetrics.landing_url)).desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    items = [{"keyword": r.keyword, "urls": int(r.urls)} for r in rows]
    return {"site_id": site_id, "items": items}


@router.get("/changes")
async def keyword_changes(site_id: int = Query(...), limit: int = Query(default=50), db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    limit = max(5, min(200, int(limit)))
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    rows = (await db.execute(
        select(KeywordMetrics.keyword, KeywordMetrics.landing_url, KeywordMetrics.position, KeywordMetrics.date)
        .where(KeywordMetrics.site_id == site_id, KeywordMetrics.position.is_not(None))
        .order_by(KeywordMetrics.keyword.asc(), KeywordMetrics.date.desc())
    )).all()

    seen: Dict[str, Tuple[Optional[float], Optional[date], Optional[float], Optional[date], Optional[str]]] = {}
    for kw, url, pos, d in rows:
        key = str(kw or "").strip()
        if not key:
            continue
        if key not in seen:
            seen[key] = (float(pos), d, None, None, url)
            continue
        cur_pos, cur_date, prev_pos, prev_date, cur_url = seen[key]
        if prev_pos is None and d != cur_date:
            seen[key] = (cur_pos, cur_date, float(pos), d, cur_url or url)

    items = []
    for kw, (cur_pos, cur_date, prev_pos, prev_date, url) in seen.items():
        if prev_pos is None:
            continue
        delta = round(float(prev_pos) - float(cur_pos), 2)
        items.append(
            {
                "keyword": kw,
                "url": url,
                "current_position": cur_pos,
                "current_date": cur_date.isoformat() if cur_date else None,
                "prev_position": prev_pos,
                "prev_date": prev_date.isoformat() if prev_date else None,
                "delta": delta,
            }
        )

    items.sort(key=lambda x: abs(float(x.get("delta") or 0)), reverse=True)
    return {"site_id": site_id, "items": items[:limit]}
