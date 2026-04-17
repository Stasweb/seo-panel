from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Tuple, List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.http_client import http_service
from app.models.models import Backlink, BacklinkStatusHistory, BacklinkCheckHistory, AppLog
from app.services.metrics_service import metrics_service
from app.services.seo_service import seo_service
from app.utils.time import utcnow


def _normalize_for_compare(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    try:
        p = urlparse(u)
        if not p.scheme:
            p = urlparse(f"https://{u}")
        host = (p.netloc or "").lower()
        path = p.path or "/"
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        return f"{host}{path}"
    except Exception:
        return u


def _extract_domain(url: str) -> str:
    try:
        p = urlparse(url)
        if not p.scheme:
            p = urlparse(f"https://{url}")
        return (p.netloc or "").lower()
    except Exception:
        return ""


def _tld_region(domain: str) -> Optional[str]:
    d = (domain or "").lower().strip()
    if not d:
        return None
    if d.endswith(".ru"):
        return "RU"
    if d.endswith(".kz"):
        return "KZ"
    return "global"


SUSPICIOUS_TLDS = {
    ".xyz",
    ".top",
    ".click",
    ".online",
    ".site",
    ".icu",
    ".monster",
    ".work",
    ".rest",
    ".info",
}


def _calc_toxic_score(*, out_links: int, https: bool, content_len: int, tld: str, indexed: Optional[bool]) -> Tuple[int, str]:
    score = 0
    if out_links >= 250:
        score += 35
    elif out_links >= 120:
        score += 20
    elif out_links >= 80:
        score += 10

    if tld in SUSPICIOUS_TLDS:
        score += 25

    if not https:
        score += 15

    if content_len < 200:
        score += 25
    elif content_len < 500:
        score += 10

    if indexed is False:
        score += 15

    if score < 0:
        score = 0
    if score > 100:
        score = 100

    flag = "safe"
    if score >= 70:
        flag = "toxic"
    elif score >= 30:
        flag = "suspicious"
    return int(score), flag


def _calc_dr(*, backlinks: int, dofollow: int, unique_anchors: int, https: bool, indexed: Optional[bool]) -> int:
    score = 10.0

    score += min(30.0, float(backlinks) * 2.0)
    score += min(20.0, float(unique_anchors) * 3.0)
    score += min(20.0, float(dofollow) * 2.0)

    if https:
        score += 10.0
    if indexed is True:
        score += 20.0
    elif indexed is False:
        score -= 10.0

    if score < 0:
        score = 0
    if score > 100:
        score = 100
    return int(round(score))


class LinkAnalysisService:
    async def analyze_one(self, db: AsyncSession, *, backlink: Backlink) -> Dict[str, object]:
        now = utcnow()
        src = (backlink.source_url or "").strip()
        tgt = (backlink.target_url or "").strip()
        is_purchased = (backlink.source or "").strip().lower() == "purchased"

        http_status: Optional[int] = None
        redirect_hops: Optional[int] = None
        link_type: Optional[str] = None
        anchor: Optional[str] = None
        out_links = 0
        content_len = 0
        prev_status = backlink.status

        if settings.TESTING:
            backlink.http_status = 200
            backlink.status = "active"
            backlink.last_checked = now
            backlink.lost_at = None
            db.add(backlink)
            if prev_status != backlink.status and backlink.id:
                db.add(BacklinkStatusHistory(backlink_id=backlink.id, status=backlink.status, changed_at=now))
            if is_purchased and backlink.id:
                db.add(
                    BacklinkCheckHistory(
                        backlink_id=backlink.id,
                        checked_at=now,
                        http_status=backlink.http_status,
                        status=backlink.status,
                        link_type=backlink.link_type,
                        outgoing_links=backlink.outgoing_links,
                        content_length=backlink.content_length,
                        domain_score=backlink.domain_score,
                        toxic_score=backlink.toxic_score,
                        toxic_flag=backlink.toxic_flag,
                    )
                )
            await db.commit()
            await db.refresh(backlink)
            return {"id": backlink.id, "http_status": backlink.http_status, "status": backlink.status}

        try:
            src_url = src if src.startswith(("http://", "https://")) else f"https://{src}"
            res = await http_service.get_text(
                src_url,
                user_agent=settings.USER_AGENT,
                cache_key=f"link_src:{src_url}",
                timeout=12.0,
                follow_redirects=True,
            )
            http_status = res.status_code
            redirect_hops = res.history_count
            if res.status_code >= 400:
                    backlink.http_status = http_status
                    backlink.status = "broken"
                    backlink.last_checked = now
                    backlink.lost_at = now
                    backlink.redirect_hops = redirect_hops
                    db.add(backlink)
                    if prev_status != backlink.status and backlink.id:
                        db.add(BacklinkStatusHistory(backlink_id=backlink.id, status=backlink.status, changed_at=now))
                    if is_purchased and backlink.id:
                        db.add(
                            BacklinkCheckHistory(
                                backlink_id=backlink.id,
                                checked_at=now,
                                http_status=backlink.http_status,
                                status=backlink.status,
                                link_type=backlink.link_type,
                                outgoing_links=backlink.outgoing_links,
                                content_length=backlink.content_length,
                                domain_score=backlink.domain_score,
                                toxic_score=backlink.toxic_score,
                                toxic_flag=backlink.toxic_flag,
                            )
                        )
                    await db.commit()
                    return {"id": backlink.id, "http_status": http_status, "status": backlink.status}

            soup = BeautifulSoup(res.text, "lxml")
            a_tags = soup.find_all("a")
            out_links = len(a_tags)
            content_len = len(soup.get_text(" ", strip=True) or "")

            tgt_norm = _normalize_for_compare(tgt)
            base_url = str(res.url)

            for a in a_tags:
                href = a.get("href")
                if not href:
                    continue
                abs_url = urljoin(base_url, href)
                if _normalize_for_compare(abs_url) == tgt_norm:
                    exists = True
                    rel = a.get("rel") or []
                    rel_join = " ".join([str(x).lower() for x in rel]) if isinstance(rel, list) else str(rel).lower()
                    link_type = "nofollow" if "nofollow" in rel_join else "dofollow"
                    anchor = a.get_text(strip=True) or None
                    break
        except Exception:
            backlink.http_status = http_status
            backlink.status = "broken"
            backlink.last_checked = now
            backlink.lost_at = now
            backlink.redirect_hops = redirect_hops
            db.add(backlink)
            if prev_status != backlink.status and backlink.id:
                db.add(BacklinkStatusHistory(backlink_id=backlink.id, status=backlink.status, changed_at=now))
            if is_purchased and backlink.id:
                db.add(
                    BacklinkCheckHistory(
                        backlink_id=backlink.id,
                        checked_at=now,
                        http_status=backlink.http_status,
                        status=backlink.status,
                        link_type=backlink.link_type,
                        outgoing_links=backlink.outgoing_links,
                        content_length=backlink.content_length,
                        domain_score=backlink.domain_score,
                        toxic_score=backlink.toxic_score,
                        toxic_flag=backlink.toxic_flag,
                    )
                )
            await db.commit()
            return {"id": backlink.id, "http_status": http_status, "status": backlink.status}

        backlink.http_status = http_status
        backlink.last_checked = now
        backlink.redirect_hops = redirect_hops
        backlink.outgoing_links = out_links
        backlink.content_length = content_len

        if not exists:
            backlink.status = "lost"
            backlink.lost_at = now
        else:
            backlink.status = "active"
            backlink.lost_at = None
            if link_type:
                backlink.link_type = link_type
            if anchor and not backlink.anchor:
                backlink.anchor = anchor

        donor = _extract_domain(src)
        region = _tld_region(donor)
        try:
            p = urlparse(src if src.startswith(("http://", "https://")) else f"https://{src}")
            https = p.scheme.lower() == "https"
        except Exception:
            https = True
        indexed = await seo_service.check_indexed(donor) if donor else None
        tld = f".{donor.split('.')[-1]}" if donor and "." in donor else ""
        toxic_score, toxic_flag = _calc_toxic_score(out_links=out_links, https=https, content_len=content_len, tld=tld, indexed=indexed)
        backlink.toxic_score = toxic_score
        backlink.toxic_flag = toxic_flag
        backlink.region = region

        db.add(backlink)
        if prev_status != backlink.status and backlink.id:
            db.add(BacklinkStatusHistory(backlink_id=backlink.id, status=backlink.status, changed_at=now))
        if is_purchased and backlink.id:
            db.add(
                BacklinkCheckHistory(
                    backlink_id=backlink.id,
                    checked_at=now,
                    http_status=backlink.http_status,
                    status=backlink.status,
                    link_type=backlink.link_type,
                    outgoing_links=backlink.outgoing_links,
                    content_length=backlink.content_length,
                    domain_score=backlink.domain_score,
                    toxic_score=backlink.toxic_score,
                    toxic_flag=backlink.toxic_flag,
                )
            )
        await db.commit()
        await db.refresh(backlink)

        return {
            "id": backlink.id,
            "http_status": backlink.http_status,
            "status": backlink.status,
            "link_type": backlink.link_type,
            "domain_score": backlink.domain_score,
            "region": backlink.region,
            "toxic_score": backlink.toxic_score,
            "toxic_flag": backlink.toxic_flag,
        }

    async def analyze_site(self, db: AsyncSession, *, site_id: int, limit: int = 500) -> Tuple[int, int, int]:
        limit = max(1, min(2000, int(limit)))
        rows = (await db.execute(
            select(Backlink).where(Backlink.site_id == site_id).order_by(Backlink.last_checked.asc(), Backlink.first_seen.asc()).limit(limit)
        )).scalars().all()

        active = 0
        lost = 0
        broken = 0
        for b in rows:
            r = await self.analyze_one(db, backlink=b)
            st = str(r.get("status") or "").lower()
            if st == "active":
                active += 1
            elif st == "lost":
                lost += 1
            else:
                broken += 1

        donors: Dict[str, List[Backlink]] = {}
        for b in rows:
            d = _extract_domain(b.source_url or "")
            if not d:
                continue
            donors.setdefault(d, []).append(b)

        for donor, bls in list(donors.items())[:150]:
            backlinks = len(bls)
            dofollow = sum(1 for x in bls if (x.link_type or "").lower() == "dofollow")
            anchors = {((x.anchor or "").strip().lower()) for x in bls if x.anchor and x.anchor.strip()}
            unique_anchors = len(anchors)
            https = any((x.source_url or "").strip().lower().startswith("https://") for x in bls)
            indexed = await seo_service.check_indexed(donor)
            dr = _calc_dr(backlinks=backlinks, dofollow=dofollow, unique_anchors=unique_anchors, https=https, indexed=indexed)
            for x in bls:
                x.domain_score = dr
                x.region = x.region or _tld_region(donor)
                db.add(x)
        await db.commit()

        all_rows = (await db.execute(select(Backlink).where(Backlink.site_id == site_id))).scalars().all()
        total = len(all_rows)
        avg_dr = 0
        toxic_pct = 0
        if total:
            dr_vals = [int(x.domain_score) for x in all_rows if x.domain_score is not None]
            avg_dr = int(round(sum(dr_vals) / max(1, len(dr_vals)))) if dr_vals else 0
            tox = sum(1 for x in all_rows if (x.toxic_flag or "") == "toxic")
            toxic_pct = round((tox / total) * 100.0, 2)
        await metrics_service.save(
            db,
            site_id=site_id,
            metric_type="links_ahrefs",
            value={"avg_dr": avg_dr, "toxic_pct": toxic_pct, "total": total, "active": active, "lost": lost, "broken": broken},
        )
        db.add(
            AppLog(
                level="INFO",
                category="links",
                method=None,
                path=None,
                status_code=None,
                message=f"links analyzed site_id={site_id} total={total} avg_dr={avg_dr} toxic_pct={toxic_pct}",
                created_at=utcnow(),
            )
        )
        await db.commit()
        return active, lost, broken


link_analysis_service = LinkAnalysisService()
