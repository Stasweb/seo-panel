from app.services.base_service import BaseService
from app.models.models import Site, Task, ContentPlan, SEOPosition
from app.schemas.schemas import SiteCreate, SiteUpdate, TaskCreate, TaskUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any

class SiteService(BaseService[Site, SiteCreate, SiteUpdate]):
    async def get_stats(self, db: AsyncSession, site_id: int) -> Dict[str, Any]:
        """
        Get various stats for a site (tasks count, content count, positions).
        """
        tasks_count = await db.scalar(
            select(func.count(Task.id)).where(Task.site_id == site_id)
        )
        content_count = await db.scalar(
            select(func.count(ContentPlan.id)).where(ContentPlan.site_id == site_id)
        )
        avg_position = await db.scalar(
            select(func.avg(SEOPosition.position)).where(SEOPosition.site_id == site_id)
        )

        return {
            "tasks_count": tasks_count or 0,
            "content_count": content_count or 0,
            "avg_position": round(float(avg_position), 2) if avg_position else 0.0
        }

class TaskService(BaseService[Task, TaskCreate, TaskUpdate]):
    pass

site_service = SiteService(Site)
task_service = TaskService(Task)
