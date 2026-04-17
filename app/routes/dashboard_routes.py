from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.dashboard_service import dashboard_service
from app.services.ip_service import ip_service
from app.services.system_info_service import system_info_service
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


@router.get("/dashboard/errors-stats")
async def errors_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Current robots/sitemap status summary for dashboard.
    """
    return await dashboard_service.get_errors_stats(db)


@router.get("/dashboard/keyword-deltas")
async def keyword_deltas(limit: int = 8, site_id: Optional[int] = None, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await dashboard_service.get_keyword_deltas(db, limit=limit, site_id=site_id)


@router.get("/dashboard/recent-errors")
async def recent_errors(limit: int = 10, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await dashboard_service.get_recent_errors(db, limit=limit)


@router.get("/dashboard/ip")
async def dashboard_ip(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await ip_service.get_current(db)


@router.get("/dashboard/ip-history")
async def dashboard_ip_history(limit: int = 50, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await ip_service.history(db, limit=limit)


@router.get("/dashboard/system")
async def dashboard_system() -> Dict[str, Any]:
    return system_info_service.get()
