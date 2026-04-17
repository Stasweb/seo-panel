from __future__ import annotations

import csv
import io
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Backlink, CompetitorBacklink
from app.utils.time import utcnow


def _norm_domain(value: str) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = s.split("/")[0]
    if s.startswith("www."):
        s = s[4:]
    return s


def _extract_domain(url: str) -> str:
    s = (url or "").strip()
    if not s:
        return ""
    if not s.startswith(("http://", "https://")):
        s = "https://" + s
    try:
        h = urlparse(s).netloc.lower()
    except Exception:
        return ""
    if h.startswith("www."):
        h = h[4:]
    return h


def _tld_region(domain: str) -> Optional[str]:
    d = (domain or "").lower()
    if d.endswith(".ru"):
        return "ru"
    if d.endswith(".kz"):
        return "kz"
    if d.endswith(".by"):
        return "by"
    if d.endswith(".ua"):
        return "ua"
    if d.endswith(".com"):
        return "com"
    if d.endswith(".org"):
        return "org"
    if d.endswith(".net"):
        return "net"
    return (d.rsplit(".", 1)[-1] if "." in d else None) or None


def _calc_dr(*, backlinks: int, dofollow: int, unique_anchors: int, https: bool) -> int:
    score = 10.0
    score += min(30.0, float(backlinks) * 2.0)
    score += min(20.0, float(unique_anchors) * 3.0)
    score += min(20.0, float(dofollow) * 2.0)
    if https:
        score += 10.0
    if score < 0:
        score = 0
    if score > 100:
        score = 100
    return int(round(score))


def _map_row(row: Dict[str, str]) -> Dict[str, Optional[str]]:
    def pick(keys: List[str]) -> Optional[str]:
        for k in keys:
            if k in row and (row.get(k) or "").strip():
                return (row.get(k) or "").strip()
        return None

    source_url = pick(["source_url", "Source URL", "Source", "Referring page URL", "From", "Referring Page URL"])
    target_url = pick(["target_url", "Target URL", "To", "Link URL", "Target", "Target url"])
    anchor = pick(["anchor", "Anchor", "Anchor text", "Anchor Text", "Anchor_text"])
    link_type = pick(["type", "link_type", "Link type", "Link Type", "Rel"])
    dr = pick(["domain_score", "dr", "DR", "Domain Rating", "Domain rating", "Ref domains DR"])
    first_seen = pick(["first_seen", "First seen", "First Seen", "First seen date", "First_seen"])

    if link_type:
        lt = link_type.strip().lower()
        if lt in {"nofollow", "dofollow", "ugc", "sponsored"}:
            link_type = lt if lt in {"nofollow", "dofollow"} else "nofollow"
        elif lt in {"true", "yes", "1"}:
            link_type = "nofollow"
        elif lt in {"false", "no", "0"}:
            link_type = "dofollow"
        else:
            link_type = "dofollow"
    else:
        link_type = "dofollow"

    return {"source_url": source_url, "target_url": target_url, "anchor": anchor, "link_type": link_type, "dr": dr, "first_seen": first_seen}


class CompetitorBacklinkService:
    async def clear(self, db: AsyncSession, *, organization_id: int, competitor_domain: str) -> int:
        dom = _norm_domain(competitor_domain)
        if not dom:
            return 0
        res = await db.execute(delete(CompetitorBacklink).where(CompetitorBacklink.organization_id == organization_id, CompetitorBacklink.competitor_domain == dom))
        await db.commit()
        return int(res.rowcount or 0)

    async def import_csv(
        self,
        db: AsyncSession,
        *,
        organization_id: int,
        competitor_domain: str,
        content_bytes: bytes,
        encoding: str = "utf-8",
        max_rows: int = 20000,
    ) -> Dict[str, Any]:
        dom = _norm_domain(competitor_domain)
        if not dom:
            return {"ok": False, "detail": "Пустой домен"}
        text = content_bytes.decode(encoding, errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        now = utcnow()

        imported = 0
        updated = 0
        errors: List[str] = []
        rows: List[Dict[str, Any]] = []
        for idx, raw in enumerate(reader, start=2):
            if idx > max_rows + 1:
                break
            mapped = _map_row({str(k): str(v) for k, v in (raw or {}).items()})
            src = (mapped.get("source_url") or "").strip()
            tgt = (mapped.get("target_url") or "").strip()
            if not src or not tgt:
                errors.append(f"Строка {idx}: пустой source_url или target_url")
                continue
            if len(src) > 1000:
                src = src[:1000]
            if len(tgt) > 1000:
                tgt = tgt[:1000]
            anchor = (mapped.get("anchor") or "").strip() or None
            lt = (mapped.get("link_type") or "dofollow").strip().lower() or "dofollow"
            dr_raw = (mapped.get("dr") or "").strip()
            dr_val: Optional[int] = None
            if dr_raw:
                try:
                    dr_val = int(float(dr_raw))
                except Exception:
                    dr_val = None
            fs_raw = (mapped.get("first_seen") or "").strip()
            fs_val: Optional[datetime] = None
            if fs_raw:
                for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
                    try:
                        fs_val = datetime.strptime(fs_raw[:19], fmt)
                        break
                    except Exception:
                        continue
            rows.append({"source_url": src, "target_url": tgt, "anchor": anchor, "link_type": lt, "domain_score": dr_val, "first_seen": fs_val})

        if not rows:
            return {"ok": True, "imported": 0, "updated": 0, "errors": errors[:50], "competitor_domain": dom}

        existing = (
            await db.execute(
                select(CompetitorBacklink.source_url, CompetitorBacklink.target_url)
                .where(CompetitorBacklink.organization_id == organization_id, CompetitorBacklink.competitor_domain == dom)
            )
        ).all()
        existing_set = {(str(a), str(b)) for a, b in existing}

        for r in rows:
            key = (r["source_url"], r["target_url"])
            if key in existing_set:
                updated += 1
                stmt = (
                    select(CompetitorBacklink)
                    .where(
                        CompetitorBacklink.organization_id == organization_id,
                        CompetitorBacklink.competitor_domain == dom,
                        CompetitorBacklink.source_url == r["source_url"],
                        CompetitorBacklink.target_url == r["target_url"],
                    )
                    .limit(1)
                )
                row = (await db.execute(stmt)).scalars().first()
                if row:
                    row.anchor = r["anchor"]
                    row.link_type = r["link_type"]
                    if r["domain_score"] is not None:
                        row.domain_score = int(r["domain_score"])
                    if r["first_seen"] is not None:
                        row.first_seen = r["first_seen"]
                    db.add(row)
                continue
            imported += 1
            db.add(
                CompetitorBacklink(
                    organization_id=organization_id,
                    competitor_domain=dom,
                    donor_domain=_extract_domain(r["source_url"]),
                    source_url=r["source_url"],
                    target_url=r["target_url"],
                    anchor=r["anchor"],
                    link_type=r["link_type"],
                    domain_score=r["domain_score"],
                    first_seen=r["first_seen"] or now,
                    region=_tld_region(_extract_domain(r["source_url"])),
                )
            )
        await db.commit()

        await self._backfill_donor_domain(db, organization_id=organization_id, competitor_domain=dom, limit_rows=20000)
        await self._calc_missing_dr(db, organization_id=organization_id, competitor_domain=dom, limit_donors=200)
        return {"ok": True, "imported": imported, "updated": updated, "errors": errors[:50], "competitor_domain": dom}

    async def _backfill_donor_domain(self, db: AsyncSession, *, organization_id: int, competitor_domain: str, limit_rows: int = 20000) -> None:
        rows = (
            await db.execute(
                select(CompetitorBacklink)
                .where(CompetitorBacklink.organization_id == organization_id, CompetitorBacklink.competitor_domain == competitor_domain)
                .limit(int(limit_rows))
            )
        ).scalars().all()
        for r in rows:
            if r.donor_domain:
                continue
            r.donor_domain = _extract_domain(r.source_url or "")
            db.add(r)
        await db.commit()

    async def _calc_missing_dr(self, db: AsyncSession, *, organization_id: int, competitor_domain: str, limit_donors: int = 200) -> None:
        rows = (
            await db.execute(
                select(CompetitorBacklink).where(CompetitorBacklink.organization_id == organization_id, CompetitorBacklink.competitor_domain == competitor_domain)
            )
        ).scalars().all()
        donors: Dict[str, List[CompetitorBacklink]] = defaultdict(list)
        for b in rows:
            d = (b.donor_domain or "").strip() or _extract_domain(b.source_url or "")
            if d:
                donors[d].append(b)
        for donor, bls in list(donors.items())[: max(1, int(limit_donors))]:
            if all(x.domain_score is not None for x in bls):
                continue
            backlinks = len(bls)
            dofollow = sum(1 for x in bls if (x.link_type or "").lower() == "dofollow")
            anchors = {((x.anchor or "").strip().lower()) for x in bls if x.anchor and x.anchor.strip()}
            unique_anchors = len(anchors)
            https = any((x.source_url or "").strip().lower().startswith("https://") for x in bls)
            dr = _calc_dr(backlinks=backlinks, dofollow=dofollow, unique_anchors=unique_anchors, https=https)
            for x in bls:
                if x.domain_score is None:
                    x.domain_score = dr
                    db.add(x)
        await db.commit()

    async def stats(
        self,
        db: AsyncSession,
        *,
        organization_id: int,
        competitor_domain: str,
        limit: int = 50,
        site_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        dom = _norm_domain(competitor_domain)
        if not dom:
            return {"ok": False, "detail": "Пустой домен"}
        limit = max(1, min(200, int(limit)))

        rows = (
            await db.execute(
                select(CompetitorBacklink).where(CompetitorBacklink.organization_id == organization_id, CompetitorBacklink.competitor_domain == dom)
            )
        ).scalars().all()
        total = len(rows)
        if total == 0:
            return {"ok": True, "competitor_domain": dom, "total": 0, "donors_total": 0, "items": {}, "overlap": None}

        link_types = Counter((b.link_type or "dofollow").lower() for b in rows)
        dofollow = int(link_types.get("dofollow", 0))
        dofollow_pct = round((dofollow / max(1, total)) * 100.0, 2)

        donors: Dict[str, List[CompetitorBacklink]] = defaultdict(list)
        for b in rows:
            d = (b.donor_domain or "").strip() or _extract_domain(b.source_url or "")
            if d:
                donors[d].append(b)
        donors_total = len(donors)

        donor_items = []
        dr_vals = []
        for donor, bls in donors.items():
            bl_total = len(bls)
            bl_dofollow = sum(1 for x in bls if (x.link_type or "").lower() == "dofollow")
            anchors = {((x.anchor or "").strip().lower()) for x in bls if x.anchor and x.anchor.strip()}
            unique_anchors = len(anchors)
            drs = [int(x.domain_score) for x in bls if x.domain_score is not None]
            avg_dr = int(round(sum(drs) / max(1, len(drs)))) if drs else 0
            max_dr = max(drs) if drs else 0
            dr_vals.extend(drs)
            donor_items.append(
                {
                    "donor": donor,
                    "backlinks": bl_total,
                    "dofollow": bl_dofollow,
                    "unique_anchors": unique_anchors,
                    "avg_dr": avg_dr,
                    "max_dr": max_dr,
                    "region": _tld_region(donor),
                }
            )

        donor_items.sort(key=lambda x: (x["backlinks"], x["avg_dr"]), reverse=True)
        top_donors = donor_items[:limit]

        anchors = Counter()
        for b in rows:
            a = (b.anchor or "").strip()
            if a:
                anchors[a.lower()] += 1
        anchor_items = []
        for a, c in anchors.most_common(limit):
            anchor_items.append({"anchor": a, "count": int(c), "pct": round((c / max(1, total)) * 100.0, 2)})

        targets = Counter()
        for b in rows:
            tgt = (b.target_url or "").strip()
            if tgt:
                targets[tgt] += 1
        top_targets = [{"url": u, "count": int(c)} for u, c in targets.most_common(min(limit, 50))]

        avg_dr_total = int(round(sum(dr_vals) / max(1, len(dr_vals)))) if dr_vals else 0
        dr_buckets = {"0-19": 0, "20-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
        for v in dr_vals:
            if v < 20:
                dr_buckets["0-19"] += 1
            elif v < 40:
                dr_buckets["20-39"] += 1
            elif v < 60:
                dr_buckets["40-59"] += 1
            elif v < 80:
                dr_buckets["60-79"] += 1
            else:
                dr_buckets["80-100"] += 1

        region_counts = Counter(x.get("region") or "?" for x in top_donors)
        top_regions = [{"region": k, "count": int(v)} for k, v in region_counts.most_common(8)]

        overlap_payload = None
        gap_payload = None
        if site_id is not None:
            srows = (await db.execute(select(Backlink.source_url).where(Backlink.site_id == int(site_id)))).all()
            sdonors = {_extract_domain(x[0] or "") for x in srows}
            sdonors.discard("")
            cdonors = set(donors.keys())
            overlap = sorted(cdonors.intersection(sdonors))
            unique = sorted(cdonors.difference(sdonors))
            overlap_payload = {
                "site_id": int(site_id),
                "overlap_count": len(overlap),
                "unique_competitor_donors_count": len(unique),
                "overlap_donors": overlap[:100],
                "unique_competitor_donors": unique[:100],
            }
            gap_payload = {
                "site_id": int(site_id),
                "donor_gap_count": len(unique),
                "donor_gap": unique[:200],
            }

        return {
            "ok": True,
            "competitor_domain": dom,
            "total": total,
            "donors_total": donors_total,
            "dofollow_pct": dofollow_pct,
            "avg_dr": avg_dr_total,
            "link_types": dict(link_types),
            "dr_buckets": dr_buckets,
            "top_donors": top_donors,
            "top_anchors": anchor_items,
            "top_targets": top_targets,
            "top_regions": top_regions,
            "overlap": overlap_payload,
            "gap": gap_payload,
        }

    async def donor_details(
        self,
        db: AsyncSession,
        *,
        organization_id: int,
        competitor_domain: str,
        donor_domain: str,
        limit: int = 200,
    ) -> Dict[str, Any]:
        dom = _norm_domain(competitor_domain)
        donor = _norm_domain(donor_domain)
        if not dom or not donor:
            return {"ok": False, "detail": "Пустой домен"}
        limit = max(1, min(500, int(limit)))
        rows = (
            await db.execute(
                select(CompetitorBacklink)
                .where(
                    CompetitorBacklink.organization_id == organization_id,
                    CompetitorBacklink.competitor_domain == dom,
                    CompetitorBacklink.donor_domain == donor,
                )
                .order_by(CompetitorBacklink.domain_score.desc().nullslast(), CompetitorBacklink.first_seen.desc())
                .limit(limit)
            )
        ).scalars().all()
        total = len(rows)
        if total == 0:
            return {"ok": True, "competitor_domain": dom, "donor_domain": donor, "total": 0, "items": [], "summary": {}}

        dofollow = sum(1 for x in rows if (x.link_type or "").lower() == "dofollow")
        anchors = Counter((x.anchor or "").strip().lower() for x in rows if (x.anchor or "").strip())
        top_anchors = [{"anchor": a, "count": int(c)} for a, c in anchors.most_common(20)]
        targets = Counter((x.target_url or "").strip() for x in rows if (x.target_url or "").strip())
        top_targets = [{"url": u, "count": int(c)} for u, c in targets.most_common(20)]
        dr_vals = [int(x.domain_score) for x in rows if x.domain_score is not None]
        avg_dr = int(round(sum(dr_vals) / max(1, len(dr_vals)))) if dr_vals else 0
        max_dr = max(dr_vals) if dr_vals else 0
        region = _tld_region(donor)

        items = []
        for x in rows:
            items.append(
                {
                    "source_url": x.source_url,
                    "target_url": x.target_url,
                    "anchor": x.anchor,
                    "link_type": x.link_type,
                    "domain_score": x.domain_score,
                    "first_seen": x.first_seen.isoformat() if x.first_seen else None,
                }
            )
        return {
            "ok": True,
            "competitor_domain": dom,
            "donor_domain": donor,
            "total": total,
            "summary": {
                "avg_dr": avg_dr,
                "max_dr": max_dr,
                "dofollow": dofollow,
                "dofollow_pct": round((dofollow / max(1, total)) * 100.0, 2),
                "unique_anchors": len(anchors),
                "region": region,
            },
            "top_anchors": top_anchors,
            "top_targets": top_targets,
            "items": items,
        }


competitor_backlink_service = CompetitorBacklinkService()
