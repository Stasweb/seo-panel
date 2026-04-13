from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Site, Task, ContentPlan, SEOPosition
from typing import Dict, Any, Optional, List


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

        # Last 5 positions changes
        last_positions = await db.execute(
            select(SEOPosition)
            .order_by(SEOPosition.check_date.desc())
            .limit(5)
        )

        positions = last_positions.scalars().all()

        return {
            "sites_count": sites_count or 0,
            "tasks_todo": tasks_todo or 0,
            "tasks_in_progress": tasks_in_progress or 0,
            "content_idea": content_idea or 0,
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
        labels: List[str] = [str(r.d) for r in rows]
        values: List[float] = [round(float(r.avg_pos or 0), 2) for r in rows]
        return {"labels": labels, "values": values}

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


dashboard_service = DashboardService()
