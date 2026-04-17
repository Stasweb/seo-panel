from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Organization, Site, User
from app.utils.time import utcnow


class OrganizationService:
    async def ensure_default(self, db: AsyncSession) -> Organization:
        org = (await db.execute(select(Organization).order_by(Organization.id.asc()).limit(1))).scalars().first()
        if org:
            return org
        org = Organization(name="Default", plan=settings.DEFAULT_PLAN, created_at=utcnow())
        db.add(org)
        await db.commit()
        await db.refresh(org)
        return org

    async def get_plan_limit(self, plan: str) -> int:
        p = (plan or "free").strip().lower()
        if p == "pro":
            return 20
        return 2

    async def can_add_site(self, db: AsyncSession, *, organization_id: int) -> bool:
        org = await db.get(Organization, organization_id)
        plan = (org.plan if org else "free") or "free"
        limit = await self.get_plan_limit(plan)
        count = int(await db.scalar(select(func.count(Site.id)).where(Site.organization_id == organization_id)) or 0)
        return count < limit

    async def attach_user(self, db: AsyncSession, *, user_id: int, organization_id: int) -> None:
        u = await db.get(User, user_id)
        if not u:
            return
        u.organization_id = organization_id
        db.add(u)
        await db.commit()


organization_service = OrganizationService()
