from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.dashboard_service import dashboard_service

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Main dashboard page.
    """
    overview = await dashboard_service.get_overview(db)
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "overview": overview}
    )

@router.get("/overview-data")
async def dashboard_overview_data(db: AsyncSession = Depends(get_db)):
    """
    API for Chart.js or other async updates.
    """
    return await dashboard_service.get_overview(db)
