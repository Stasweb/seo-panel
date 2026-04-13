from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.dashboard_service import dashboard_service
from app.schemas.schemas import DashboardResponse
from typing import Optional, Dict, Any

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard_overview(db: AsyncSession = Depends(get_db)):
    """
    Dashboard aggregated metrics.
    """
    return await dashboard_service.get_overview(db)


@router.get("/dashboard/positions-history")
async def positions_history(site_id: Optional[int] = None, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Average position history for charts.
    """
    return await dashboard_service.get_positions_history(db, site_id=site_id)


@router.get("/dashboard/tasks-stats")
async def tasks_stats(site_id: Optional[int] = None, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Task status distribution for charts.
    """
    return await dashboard_service.get_tasks_stats(db, site_id=site_id)
