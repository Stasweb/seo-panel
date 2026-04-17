from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Site, Backlink, MetricHistory
from app.services.internal_linking_service import internal_linking_service


router = APIRouter(prefix="/domain-analysis", tags=["domain-analysis"])


@router.get("/{domain}")
async def domain_analysis(domain: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    dom = (domain or "").strip().lower()
    site = (await db.execute(select(Site).where(Site.domain == dom))).scalars().first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    total_backlinks = int(await db.scalar(select(func.count(Backlink.id)).where(Backlink.site_id == site.id)) or 0)
    referring_domains = (await db.execute(select(Backlink.source_url).where(Backlink.site_id == site.id))).all()
    donors = set()
    for (u,) in referring_domains:
        if not u:
            continue
        parts = str(u).split("/")
        host = parts[2] if len(parts) > 2 and parts[0].startswith("http") else parts[0]
        host = host.replace("https://", "").replace("http://", "").split(":")[0].lower()
        if host:
            donors.add(host)

    anchors_rows = (await db.execute(select(Backlink.anchor).where(Backlink.site_id == site.id))).all()
    counts: Dict[str, int] = {}
    for (a,) in anchors_rows:
        if not a:
            continue
        k = str(a).strip()
        if not k:
            continue
        counts[k] = counts.get(k, 0) + 1
    top_anchors = [{"anchor": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:20]]

    regions_rows = (await db.execute(select(Backlink.region, func.count(Backlink.id)).where(Backlink.site_id == site.id).group_by(Backlink.region))).all()
    regions = [{"region": (r or "unknown"), "count": int(c)} for r, c in regions_rows]

    last_metric = (await db.execute(
        select(MetricHistory).where(MetricHistory.site_id == site.id, MetricHistory.metric_type == "links_ahrefs").order_by(MetricHistory.created_at.desc()).limit(1)
    )).scalars().first()
    dr = int(((last_metric.value_json or {}).get("avg_dr") or 0)) if last_metric else 0

    return {
        "site_id": site.id,
        "domain": site.domain,
        "dr": dr,
        "backlinks": total_backlinks,
        "referring_domains": len(donors),
        "top_anchors": top_anchors,
        "regions": regions,
    }


@router.get("/{domain}/internal-links")
async def internal_links(domain: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    dom = (domain or "").strip().lower()
    site = (await db.execute(select(Site).where(Site.domain == dom))).scalars().first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await internal_linking_service.analyze_home(domain=site.domain)
