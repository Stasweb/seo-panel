from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Backlink, BacklinkStatusHistory
from app.utils.time import utcnow


def _ensure_http(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return f"https://{u}"


def _donor_domain(source_url: str) -> str:
    try:
        p = urlparse(_ensure_http(source_url))
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


def _compare_state(*, now: datetime, b: Backlink) -> str:
    st = (b.status or "").lower()
    if st == "lost" or st == "broken":
        return "LOST"
    if st == "active" and b.first_seen and now - b.first_seen <= timedelta(hours=6):
        return "NEW"
    return "OK"


class LinkService:
    async def _record_status(self, db: AsyncSession, *, backlink_id: int, status: str, now: datetime) -> None:
        db.add(BacklinkStatusHistory(backlink_id=backlink_id, status=status, changed_at=now))

    async def upsert(
        self,
        db: AsyncSession,
        *,
        site_id: int,
        source_url: str,
        target_url: str,
        anchor: Optional[str],
        link_type: Optional[str],
        domain_score: Optional[int] = None,
        source: str,
        now: Optional[datetime] = None,
    ) -> Backlink:
        now = now or utcnow()
        source_url = (source_url or "").strip()
        target_url = (target_url or "").strip()
        anchor = (anchor or "").strip() or None
        link_type = (link_type or "dofollow").strip().lower()
        if link_type not in ("dofollow", "nofollow"):
            link_type = "dofollow"
        source = (source or "manual").strip().lower()
        if source not in ("gsc", "yandex", "manual", "import", "purchased", "ahrefs"):
            source = "manual"

        row = (await db.execute(
            select(Backlink).where(
                Backlink.site_id == site_id,
                Backlink.source_url == source_url,
                Backlink.target_url == target_url,
                Backlink.source == source,
            )
        )).scalars().first()

        if row:
            prev_status = row.status
            if anchor and not row.anchor:
                row.anchor = anchor
            if link_type:
                row.link_type = link_type
            if domain_score is not None and row.domain_score is None:
                row.domain_score = int(domain_score)
            if row.status in (None, "", "lost"):
                row.status = "active"
                row.lost_at = None
            row.last_checked = now
            db.add(row)
            if prev_status != row.status:
                await self._record_status(db, backlink_id=row.id, status=row.status, now=now)
            await db.commit()
            await db.refresh(row)
            return row

        row = Backlink(
            site_id=site_id,
            source_url=source_url,
            target_url=target_url,
            anchor=anchor,
            link_type=link_type,
            status="active",
            source=source,
            first_seen=now,
            last_checked=now,
            domain_score=int(domain_score) if domain_score is not None else None,
            region=_tld_region(_donor_domain(source_url)),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        await self._record_status(db, backlink_id=row.id, status=row.status, now=now)
        await db.commit()
        return row

    async def list(
        self,
        db: AsyncSession,
        *,
        site_id: int,
        source: Optional[str] = None,
        status: Optional[str] = None,
        link_type: Optional[str] = None,
        toxic: Optional[str] = None,
        compare: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(2000, int(limit)))
        stmt = select(Backlink).where(Backlink.site_id == site_id).order_by(Backlink.first_seen.desc()).limit(limit)
        if source:
            stmt = stmt.where(Backlink.source == source)
        if status:
            stmt = stmt.where(Backlink.status == status)
        if link_type:
            stmt = stmt.where(Backlink.link_type == link_type)
        if toxic:
            stmt = stmt.where(Backlink.toxic_flag == toxic)
        if q:
            qv = f"%{q.strip()}%"
            stmt = stmt.where((Backlink.source_url.ilike(qv)) | (Backlink.target_url.ilike(qv)) | (Backlink.anchor.ilike(qv)))

        rows = (await db.execute(stmt)).scalars().all()
        now = utcnow()

        out: List[Dict[str, Any]] = []
        for b in rows:
            donor = _donor_domain(b.source_url)
            cmp_state = _compare_state(now=now, b=b)
            if compare and cmp_state != compare:
                continue
            out.append(
                {
                    "id": b.id,
                    "site_id": b.site_id,
                    "source_url": b.source_url,
                    "target_url": b.target_url,
                    "donor": donor,
                    "anchor": b.anchor,
                    "link_type": b.link_type,
                    "status": b.status,
                    "source": b.source,
                    "first_seen": b.first_seen.isoformat() if b.first_seen else None,
                    "last_checked": b.last_checked.isoformat() if b.last_checked else None,
                    "http_status": b.http_status,
                    "redirect_hops": b.redirect_hops,
                    "toxic_score": b.toxic_score,
                    "toxic_flag": b.toxic_flag,
                    "domain_score": b.domain_score,
                    "region": b.region or _tld_region(donor),
                    "compare": cmp_state,
                }
            )
        return out

    async def mark_lost_missing_from_snapshot(
        self,
        db: AsyncSession,
        *,
        site_id: int,
        source: str,
        present_pairs: List[Tuple[str, str]],
        now: Optional[datetime] = None,
    ) -> int:
        now = now or utcnow()
        present = {(a.strip(), b.strip()) for a, b in present_pairs if a and b}
        rows = (await db.execute(
            select(Backlink).where(Backlink.site_id == site_id, Backlink.source == source)
        )).scalars().all()

        changed = 0
        for b in rows:
            key = (b.source_url, b.target_url)
            if key in present:
                continue
            if (b.status or "").lower() != "lost":
                b.status = "lost"
                b.last_checked = now
                b.lost_at = now
                db.add(b)
                await self._record_status(db, backlink_id=b.id, status=b.status, now=now)
                changed += 1

        if changed:
            await db.commit()
        return changed

    async def stats(self, db: AsyncSession, *, site_id: int, days: int = 30) -> Dict[str, Any]:
        days = max(7, min(365, int(days)))
        from_dt = utcnow() - timedelta(days=days)
        rows = (await db.execute(
            select(Backlink).where(Backlink.site_id == site_id, Backlink.first_seen >= from_dt).order_by(Backlink.first_seen.asc())
        )).scalars().all()

        lost_rows = (await db.execute(
            select(Backlink).where(
                Backlink.site_id == site_id,
                Backlink.status == "lost",
                Backlink.lost_at.is_not(None),
                Backlink.lost_at >= from_dt,
            ).order_by(Backlink.lost_at.asc())
        )).scalars().all()

        by_new: Dict[date, int] = {}
        for b in rows:
            if not b.first_seen:
                continue
            d = b.first_seen.date()
            by_new[d] = by_new.get(d, 0) + 1

        by_lost: Dict[date, int] = {}
        for b in lost_rows:
            if not b.lost_at:
                continue
            d = b.lost_at.date()
            by_lost[d] = by_lost.get(d, 0) + 1

        labels: List[str] = []
        new_counts: List[int] = []
        lost_counts: List[int] = []

        today = utcnow().date()
        start = today - timedelta(days=days - 1)
        for i in range(days):
            d = start + timedelta(days=i)
            labels.append(d.isoformat())
            new_counts.append(int(by_new.get(d, 0)))
            lost_counts.append(int(by_lost.get(d, 0)))

        total = int(await db.scalar(select(func.count(Backlink.id)).where(Backlink.site_id == site_id)) or 0)
        active = int(
            await db.scalar(select(func.count(Backlink.id)).where(Backlink.site_id == site_id, Backlink.status == "active"))
            or 0
        )
        lost = int(
            await db.scalar(select(func.count(Backlink.id)).where(Backlink.site_id == site_id, Backlink.status == "lost"))
            or 0
        )
        broken = int(
            await db.scalar(select(func.count(Backlink.id)).where(Backlink.site_id == site_id, Backlink.status == "broken"))
            or 0
        )

        return {
            "site_id": site_id,
            "labels": labels,
            "new": new_counts,
            "lost": lost_counts,
            "totals": {"all": total, "active": active, "lost": lost, "broken": broken},
        }


link_service = LinkService()
