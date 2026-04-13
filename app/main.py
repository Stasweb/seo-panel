from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.core.config import settings
from app.core.database import Base, engine
from app.routes import site_routes, dashboard_routes, seo_routes
from app.services.seo_service import seo_service
from app.core.database import AsyncSessionLocal
from app.models.models import Site, SEOAudit
from sqlalchemy import select
from datetime import datetime
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Mini SEO CRM + Analytics Studio",
    version="1.0.0"
)

# Static files and Templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include Routers
app.include_router(dashboard_routes.router)
app.include_router(site_routes.router)
app.include_router(seo_routes.router)

@app.on_event("startup")
async def startup():
    """
    Initialize database and start background scheduler.
    """
    async with engine.begin() as conn:
        # Create tables if not exist
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized")
    # Start background task for periodic site checks
    # asyncio.create_task(periodic_site_check())

async def periodic_site_check():
    """
    Simple internal scheduler for checking sites status.
    """
    while True:
        logger.info("Running periodic site audit...")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Site))
            sites = result.scalars().all()
            
            for site in sites:
                try:
                    audit = await seo_service.check_url(site.domain)
                    # Update or create audit record
                    new_audit = SEOAudit(
                        site_id=site.id,
                        url=audit.url,
                        status_code=audit.status_code,
                        title=audit.title,
                        title_length=audit.title_length,
                        h1=audit.h1,
                        is_indexed=audit.is_indexed,
                        last_check=datetime.utcnow()
                    )
                    db.add(new_audit)
                    await db.commit()
                except Exception as e:
                    logger.error(f"Error checking site {site.domain}: {e}")
                    
        # Sleep for specified interval (default 24h)
        await asyncio.sleep(settings.CHECK_INTERVAL_HOURS * 3600)

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow()}

# Middleware for simple context (like version)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
