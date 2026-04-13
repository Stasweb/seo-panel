from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from app.core.config import settings
from app.core.database import Base, engine
from app.routes import site_routes, dashboard_routes, seo_routes
from app.routes import auth_routes, ai_routes
from app.services.seo_service import seo_service
from app.core.database import AsyncSessionLocal
from app.models.models import Site, SEOAudit
from sqlalchemy import select
from datetime import datetime
import asyncio
import logging
from pathlib import Path
from app.core.security import AuthMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Mini SEO CRM + Analytics Studio",
    version="1.0.0"
)

app.add_middleware(AuthMiddleware)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include JSON API Routers under /api
app.include_router(dashboard_routes.router, prefix="/api")
app.include_router(site_routes.router, prefix="/api")
app.include_router(seo_routes.router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api")
app.include_router(ai_routes.router, prefix="/api")

@app.get("/")
async def index():
    """
    Serve dashboard HTML as a static file.
    """
    return FileResponse(str(TEMPLATES_DIR / "dashboard.html"))

@app.get("/sites")
async def sites_page():
    """
    Serve sites management HTML as a static file.
    """
    return FileResponse(str(TEMPLATES_DIR / "sites.html"))

@app.get("/login")
async def login_page():
    """
    Serve login HTML as a static file.
    """
    return FileResponse(str(TEMPLATES_DIR / "login.html"))

@app.get("/logout")
async def logout():
    """
    Clear session cookie and redirect to login.
    """
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    return resp

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
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
