from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Site, Task, ContentPlan, SEOPosition
from typing import Dict, Any, List

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
            select(SEOPosition).order_by(SEOPosition.check_date.desc()).limit(5)
        )
        
        return {
            "sites_count": sites_count or 0,
            "tasks_todo": tasks_todo or 0,
            "tasks_in_progress": tasks_in_progress or 0,
            "content_idea": content_idea or 0,
            "last_positions": last_positions.scalars().all()
        }

dashboard_service = DashboardService()
