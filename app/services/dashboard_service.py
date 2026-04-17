from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Site, Task, ContentPlan, SEOPosition, MetricHistory, SiteScanHistory, KeywordMetrics, AppLog
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


class DashboardService:
    async def get_overview(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get overview for all sites.
        """

        sites_count = await db.scalar(select(func.count(Site.id)))

        tasks_todo = await db.scalar(
            select(func.count(Task.id)).where(Task.status == "todo")
        )

        tasks_in_progress = await db.scalar(
            select(func.count(Task.id)).where(Task.status == "in_progress")
        )

        content_idea = await db.scalar(
            select(func.count(ContentPlan.id)).where(ContentPlan.status == "idea")
        )

        task_status_rows = (await db.execute(select(Task.status, func.count(Task.id)).group_by(Task.status))).all()
        content_status_rows = (await db.execute(select(ContentPlan.status, func.count(ContentPlan.id)).group_by(ContentPlan.status))).all()
        positions_count = await db.scalar(select(func.count(SEOPosition.id)))
        since = utcnow() - timedelta(days=1)
        scans_24h = await db.scalar(select(func.count(SiteScanHistory.id)).where(SiteScanHistory.created_at >= since))

        # Last 5 positions changes
        last_positions = await db.execute(
            select(SEOPosition)
            .order_by(SEOPosition.check_date.desc())
            .limit(5)
        )

        positions = last_positions.scalars().all()
        if not positions:
            km_rows = await db.execute(
                select(KeywordMetrics)
                .where(KeywordMetrics.position.is_not(None))
                .order_by(KeywordMetrics.date.desc(), KeywordMetrics.created_at.desc())
                .limit(5)
            )
            km = km_rows.scalars().all()
            return {
                "sites_count": sites_count or 0,
                "tasks_todo": tasks_todo or 0,
                "tasks_in_progress": tasks_in_progress or 0,
                "content_idea": content_idea or 0,
                "positions_count": positions_count or 0,
                "scans_24h": scans_24h or 0,
                "last_positions": [
                    {"keyword": r.keyword, "position": r.position, "check_date": r.date, "source": r.source} for r in km
                ],
            }

        logger.info(
            "dashboard_overview sites_count=%s tasks_todo=%s tasks_in_progress=%s content_idea=%s last_positions=%s",
            sites_count,
            tasks_todo,
            tasks_in_progress,
            content_idea,
            len(positions),
        )
        logger.debug(
            "dashboard_debug task_status=%s content_status=%s positions_count=%s scans_24h=%s",
            task_status_rows,
            content_status_rows,
            positions_count,
            scans_24h,
        )

        return {
            "sites_count": sites_count or 0,
            "tasks_todo": tasks_todo or 0,
            "tasks_in_progress": tasks_in_progress or 0,
            "content_idea": content_idea or 0,
            "positions_count": positions_count or 0,
            "scans_24h": scans_24h or 0,
            "last_positions": [
                {
                    "keyword": p.keyword,
                    "position": p.position,
                    "check_date": p.check_date,
                    "source": p.source,
                }
                for p in positions
            ],
        }

    async def get_positions_history(self, db: AsyncSession, site_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Return average positions history grouped by date.
        """
        stmt = (
            select(
                SEOPosition.check_date.label("d"),
                func.avg(SEOPosition.position).label("avg_pos"),
            )
            .group_by(SEOPosition.check_date)
            .order_by(SEOPosition.check_date.asc())
        )
        if site_id is not None:
            stmt = stmt.where(SEOPosition.site_id == site_id)

        rows = (await db.execute(stmt)).all()
        if rows:
            labels: List[str] = [str(r.d) for r in rows]
            values: List[float] = [round(float(r.avg_pos or 0), 2) for r in rows]
            return {"labels": labels, "values": values, "label": "Средняя позиция", "reverse_y": True}

        km_stmt = (
            select(
                KeywordMetrics.date.label("d"),
                func.avg(KeywordMetrics.position).label("avg_pos"),
            )
            .where(KeywordMetrics.position.is_not(None))
            .group_by(KeywordMetrics.date)
            .order_by(KeywordMetrics.date.asc())
        )
        if site_id is not None:
            km_stmt = km_stmt.where(KeywordMetrics.site_id == site_id)
        km_rows = (await db.execute(km_stmt)).all()
        if km_rows:
            labels_km: List[str] = [str(r.d) for r in km_rows]
            values_km: List[float] = [round(float(r.avg_pos or 0), 2) for r in km_rows]
            return {"labels": labels_km, "values": values_km, "label": "Средняя позиция", "reverse_y": True}

        scan_stmt = (
            select(
                func.date(SiteScanHistory.created_at).label("d"),
                func.avg(SiteScanHistory.health_score).label("avg_score"),
            )
            .where(SiteScanHistory.health_score.is_not(None))
            .group_by(func.date(SiteScanHistory.created_at))
            .order_by(func.date(SiteScanHistory.created_at).asc())
        )
        if site_id is not None:
            scan_stmt = scan_stmt.where(SiteScanHistory.site_id == site_id)
        scan_rows = (await db.execute(scan_stmt)).all()
        labels2: List[str] = [str(r.d) for r in scan_rows]
        values2: List[float] = [round(float(r.avg_score or 0), 2) for r in scan_rows]
        return {"labels": labels2, "values": values2, "label": "Средняя оценка здоровья", "reverse_y": False}

    async def get_tasks_stats(self, db: AsyncSession, site_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Return tasks statistics (todo / in_progress / done).
        """
        base = select(Task.status, func.count(Task.id)).group_by(Task.status)
        if site_id is not None:
            base = base.where(Task.site_id == site_id)

        rows = (await db.execute(base)).all()
        counts = {status: count for status, count in rows}
        return {
            "todo": int(counts.get("todo", 0)),
            "in_progress": int(counts.get("in_progress", 0)),
            "done": int(counts.get("done", 0)),
        }

    async def get_errors_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Return current errors summary based on latest robots/sitemap metrics per site.
        """
        rows = await db.execute(
            select(MetricHistory)
            .where(MetricHistory.metric_type.in_(["robots", "sitemap"]))
            .order_by(MetricHistory.created_at.desc())
            .limit(500)
        )
        items = rows.scalars().all()

        latest: Dict[tuple[int, str], MetricHistory] = {}
        for it in items:
            key = (it.site_id, it.metric_type)
            if key not in latest:
                latest[key] = it

        ok = 0
        warning = 0
        error = 0
        sitemap_errors_total = 0

        for (site_id, metric_type), it in latest.items():
            value = it.value_json or {}
            status = (value.get("status") or "").upper()
            if status == "OK":
                ok += 1
            elif status == "WARNING":
                warning += 1
            elif status == "ERROR":
                error += 1

            if metric_type == "sitemap":
                errs = value.get("errors") or []
                if isinstance(errs, list):
                    sitemap_errors_total += len(errs)

        return {
            "ok": ok,
            "warning": warning,
            "error": error,
            "sitemap_errors_total": sitemap_errors_total,
        }

    async def get_keyword_deltas(self, db: AsyncSession, *, limit: int = 8, site_id: Optional[int] = None) -> Dict[str, Any]:
        limit = max(3, min(100, int(limit)))
        stmt = (
            select(KeywordMetrics.keyword, KeywordMetrics.landing_url, KeywordMetrics.position, KeywordMetrics.date)
            .where(KeywordMetrics.position.is_not(None))
            .order_by(KeywordMetrics.keyword.asc(), KeywordMetrics.date.desc(), KeywordMetrics.created_at.desc())
        )
        if site_id is not None:
            stmt = stmt.where(KeywordMetrics.site_id == site_id)
        rows = (await db.execute(stmt)).all()

        seen: Dict[str, Tuple[Optional[float], Optional[datetime], Optional[float], Optional[datetime], Optional[str]]] = {}
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

    async def get_recent_errors(self, db: AsyncSession, *, limit: int = 10) -> Dict[str, Any]:
        limit = max(3, min(100, int(limit)))
        rows = (
            await db.execute(
                select(AppLog)
                .where(
                    (AppLog.level == "ERROR")
                    | ((AppLog.level == "WARNING") & (AppLog.category.is_not(None)) & (AppLog.category != "http"))
                )
                .order_by(AppLog.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return {
            "items": [
                {
                    "id": r.id,
                    "level": r.level,
                    "category": r.category,
                    "path": r.path,
                    "status_code": r.status_code,
                    "message": r.message,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        }


dashboard_service = DashboardService()
