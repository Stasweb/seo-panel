from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from app.core.config import settings
from app.core.database import Base, engine
from app.routes import site_routes, dashboard_routes, seo_routes
from app.routes import auth_routes, ai_routes
from app.routes import scan_routes
from app.routes import webmaster_routes
from app.routes import link_routes
from app.routes import integration_routes
from app.routes import user_routes
from app.routes import domain_routes
from app.routes import note_routes
from app.routes import recommendations_routes
from app.routes import notification_routes
from app.routes import keyword_routes
from app.routes import log_routes
from app.routes import competitor_routes
from app.routes import purchased_links_routes
from app.routes import task_routes
from app.routes import content_plan_routes
from app.services.seo_service import seo_service
from app.services.site_scan_service import site_scan_service
from app.services.webmaster_service import webmaster_service
from app.services.tech_audit_service import tech_audit_service
from app.services.link_analysis_service import link_analysis_service
from app.services.alert_service import alert_service
from app.services.organization_service import organization_service
from app.services.integrations_service import integrations_service
from app.core.database import AsyncSessionLocal
from app.models.models import Site, SEOAudit, User, AppLog
from sqlalchemy import select, text
from datetime import datetime
import asyncio
import logging
from pathlib import Path
from app.core.security import AuthMiddleware
from app.utils.time import utcnow

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
app.include_router(scan_routes.router, prefix="/api")
app.include_router(webmaster_routes.router, prefix="/api")
app.include_router(link_routes.router, prefix="/api")
app.include_router(integration_routes.router, prefix="/api")
app.include_router(user_routes.router, prefix="/api")
app.include_router(domain_routes.router, prefix="/api")
app.include_router(note_routes.router, prefix="/api")
app.include_router(recommendations_routes.router, prefix="/api")
app.include_router(notification_routes.router, prefix="/api")
app.include_router(keyword_routes.router, prefix="/api")
app.include_router(log_routes.router, prefix="/api")
app.include_router(competitor_routes.router, prefix="/api")
app.include_router(purchased_links_routes.router, prefix="/api")
app.include_router(task_routes.router, prefix="/api")
app.include_router(content_plan_routes.router, prefix="/api")

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

@app.get("/links")
async def links_page():
    return FileResponse(str(TEMPLATES_DIR / "links.html"))

@app.get("/purchased-links")
async def purchased_links_page():
    return FileResponse(str(TEMPLATES_DIR / "purchased_links.html"))

@app.get("/users")
async def users_page():
    return FileResponse(str(TEMPLATES_DIR / "users.html"))

@app.get("/domain-analysis/{domain}")
async def domain_analysis_page(domain: str):
    return FileResponse(str(TEMPLATES_DIR / "domain_analysis.html"))

@app.get("/notes")
async def notes_page():
    return FileResponse(str(TEMPLATES_DIR / "notes.html"))

@app.get("/recommendations/{site_id}")
async def recommendations_page(site_id: int):
    return FileResponse(str(TEMPLATES_DIR / "recommendations.html"))

@app.get("/keywords")
async def keywords_page():
    return FileResponse(str(TEMPLATES_DIR / "keywords.html"))

@app.get("/logs")
async def logs_page():
    return FileResponse(str(TEMPLATES_DIR / "logs.html"))

@app.get("/competitors")
async def competitors_page():
    return FileResponse(str(TEMPLATES_DIR / "competitors.html"))

@app.get("/tasks")
async def tasks_page():
    return FileResponse(str(TEMPLATES_DIR / "tasks.html"))

@app.get("/content-plans")
async def content_plans_page():
    return FileResponse(str(TEMPLATES_DIR / "content_plans.html"))

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
        if "sqlite" in settings.DATABASE_URL:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
            await conn.execute(text("PRAGMA foreign_keys=ON;"))

            async def _ensure_column(table: str, column: str, ddl: str) -> None:
                cols = await conn.execute(text(f"PRAGMA table_info({table})"))
                names = {str(r[1]) for r in cols.fetchall()}
                if column not in names:
                    await conn.execute(text(ddl))

            await _ensure_column("users", "role", "ALTER TABLE users ADD COLUMN role VARCHAR(20)")
            await _ensure_column("users", "created_at", "ALTER TABLE users ADD COLUMN created_at DATETIME")
            await _ensure_column("users", "organization_id", "ALTER TABLE users ADD COLUMN organization_id INTEGER")
            await _ensure_column("users", "email", "ALTER TABLE users ADD COLUMN email VARCHAR(255)")
            await _ensure_column("users", "oauth_provider", "ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(20)")
            await _ensure_column("users", "oauth_subject", "ALTER TABLE users ADD COLUMN oauth_subject VARCHAR(255)")

            await _ensure_column("sites", "organization_id", "ALTER TABLE sites ADD COLUMN organization_id INTEGER")
            await _ensure_column("sites", "email_alerts_enabled", "ALTER TABLE sites ADD COLUMN email_alerts_enabled BOOLEAN")
            await _ensure_column("sites", "alert_email", "ALTER TABLE sites ADD COLUMN alert_email VARCHAR(255)")
            await _ensure_column("sites", "user_agent_choice", "ALTER TABLE sites ADD COLUMN user_agent_choice VARCHAR(20)")
            await _ensure_column("sites", "custom_user_agent", "ALTER TABLE sites ADD COLUMN custom_user_agent TEXT")
            await _ensure_column("sites", "scan_priority", "ALTER TABLE sites ADD COLUMN scan_priority VARCHAR(20)")
            await _ensure_column("sites", "respect_robots_txt", "ALTER TABLE sites ADD COLUMN respect_robots_txt BOOLEAN")
            await _ensure_column("sites", "use_sitemap", "ALTER TABLE sites ADD COLUMN use_sitemap BOOLEAN")
            await _ensure_column("sites", "scan_pause_ms", "ALTER TABLE sites ADD COLUMN scan_pause_ms INTEGER")
            await _ensure_column("gsc_accounts", "selected_account_email", "ALTER TABLE gsc_accounts ADD COLUMN selected_account_email VARCHAR(255)")
            await _ensure_column("yandex_accounts", "selected_account_login", "ALTER TABLE yandex_accounts ADD COLUMN selected_account_login VARCHAR(255)")
            await _ensure_column("notes", "color", "ALTER TABLE notes ADD COLUMN color VARCHAR(20)")
            await _ensure_column("keyword_metrics", "landing_url", "ALTER TABLE keyword_metrics ADD COLUMN landing_url VARCHAR(1000)")
            await _ensure_column("keyword_metrics", "frequency", "ALTER TABLE keyword_metrics ADD COLUMN frequency INTEGER")
            await _ensure_column("tasks", "priority", "ALTER TABLE tasks ADD COLUMN priority VARCHAR(20)")
            await _ensure_column("tasks", "source_url", "ALTER TABLE tasks ADD COLUMN source_url VARCHAR(1000)")
            await _ensure_column("tasks", "deep_audit_report_id", "ALTER TABLE tasks ADD COLUMN deep_audit_report_id INTEGER")
            await _ensure_column("competitor_backlinks", "donor_domain", "ALTER TABLE competitor_backlinks ADD COLUMN donor_domain VARCHAR(255)")
            await _ensure_column("ahrefs_accounts", "api_key", "ALTER TABLE ahrefs_accounts ADD COLUMN api_key VARCHAR(2000)")
            await _ensure_column("ahrefs_accounts", "enabled", "ALTER TABLE ahrefs_accounts ADD COLUMN enabled BOOLEAN")
            await _ensure_column("ahrefs_accounts", "updated_at", "ALTER TABLE ahrefs_accounts ADD COLUMN updated_at DATETIME")
            await _ensure_column("gsc_accounts", "refresh_token", "ALTER TABLE gsc_accounts ADD COLUMN refresh_token VARCHAR(2000)")
            await _ensure_column("gsc_accounts", "token_expires_at", "ALTER TABLE gsc_accounts ADD COLUMN token_expires_at DATETIME")
            await _ensure_column("backlink_check_history", "backlink_id", "ALTER TABLE backlink_check_history ADD COLUMN backlink_id INTEGER")
            await _ensure_column("backlink_check_history", "checked_at", "ALTER TABLE backlink_check_history ADD COLUMN checked_at DATETIME")
            await _ensure_column("backlink_check_history", "http_status", "ALTER TABLE backlink_check_history ADD COLUMN http_status INTEGER")
            await _ensure_column("backlink_check_history", "status", "ALTER TABLE backlink_check_history ADD COLUMN status VARCHAR(20)")
            await _ensure_column("backlink_check_history", "link_type", "ALTER TABLE backlink_check_history ADD COLUMN link_type VARCHAR(20)")
            await _ensure_column("backlink_check_history", "outgoing_links", "ALTER TABLE backlink_check_history ADD COLUMN outgoing_links INTEGER")
            await _ensure_column("backlink_check_history", "content_length", "ALTER TABLE backlink_check_history ADD COLUMN content_length INTEGER")
            await _ensure_column("backlink_check_history", "domain_score", "ALTER TABLE backlink_check_history ADD COLUMN domain_score INTEGER")
            await _ensure_column("backlink_check_history", "toxic_score", "ALTER TABLE backlink_check_history ADD COLUMN toxic_score INTEGER")
            await _ensure_column("backlink_check_history", "toxic_flag", "ALTER TABLE backlink_check_history ADD COLUMN toxic_flag VARCHAR(20)")

            await _ensure_column("backlinks", "lost_at", "ALTER TABLE backlinks ADD COLUMN lost_at DATETIME")
            await _ensure_column("backlinks", "redirect_hops", "ALTER TABLE backlinks ADD COLUMN redirect_hops INTEGER")
            await _ensure_column("backlinks", "outgoing_links", "ALTER TABLE backlinks ADD COLUMN outgoing_links INTEGER")
            await _ensure_column("backlinks", "content_length", "ALTER TABLE backlinks ADD COLUMN content_length INTEGER")
            await _ensure_column("backlinks", "toxic_score", "ALTER TABLE backlinks ADD COLUMN toxic_score INTEGER")
            await _ensure_column("backlinks", "toxic_flag", "ALTER TABLE backlinks ADD COLUMN toxic_flag VARCHAR(20)")

            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_backlinks_site_status ON backlinks (site_id, status)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_backlinks_site_last_checked ON backlinks (site_id, last_checked)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notification_events_org_created ON notification_events (organization_id, created_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notes_user_created ON notes (user_id, created_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_app_logs_created_at ON app_logs (created_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_app_logs_level_category ON app_logs (level, category)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_app_settings_key ON app_settings (key)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_oauth ON users (oauth_provider, oauth_subject)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_deep_audit_org_final_created ON deep_audit_reports (organization_id, final_url, created_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_comp_bl_org_dom_donor ON competitor_backlinks (organization_id, competitor_domain, donor_domain)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ip_address_snapshots_created_at ON ip_address_snapshots (created_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ahrefs_accounts_site_id ON ahrefs_accounts (site_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_backlink_check_history_bl_at ON backlink_check_history (backlink_id, checked_at)"))

    logger.info("Database initialized")

    async with AsyncSessionLocal() as db:
        org = await organization_service.ensure_default(db)
        await db.execute(text("UPDATE sites SET organization_id = :org_id WHERE organization_id IS NULL"), {"org_id": org.id})
        await db.commit()
        admin = (await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))).scalars().first()
        if not admin:
            admin = User(
                username=settings.ADMIN_USERNAME,
                password_hash=settings.ADMIN_PASSWORD_HASH,
                role="admin",
                is_active=True,
                created_at=utcnow(),
                organization_id=org.id,
            )
            db.add(admin)
            await db.commit()
        else:
            changed = False
            if admin.role != "admin":
                admin.role = "admin"
                changed = True
            if admin.organization_id is None:
                admin.organization_id = org.id
                changed = True
            if settings.ADMIN_PASSWORD_HASH and admin.password_hash != settings.ADMIN_PASSWORD_HASH:
                admin.password_hash = settings.ADMIN_PASSWORD_HASH
                changed = True
            if changed:
                db.add(admin)
                await db.commit()
    # Start background task for periodic site checks
    if not settings.TESTING:
        asyncio.create_task(periodic_site_check())


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = utcnow()
    try:
        response = await call_next(request)
        status_code = int(response.status_code)
    except Exception as e:
        status_code = 500
        async with AsyncSessionLocal() as db:
            db.add(
                AppLog(
                    level="ERROR",
                    category="error",
                    method=request.method,
                    path=request.url.path,
                    status_code=500,
                    message=str(e),
                    created_at=utcnow(),
                )
            )
            await db.commit()
        raise

    noisy_paths = {
        "/health",
        "/api/notifications/recent",
    }
    if (not request.url.path.startswith("/static/")) and request.url.path not in noisy_paths:
        elapsed_ms = int((utcnow() - start).total_seconds() * 1000)
        level = "ERROR" if status_code >= 500 else ("WARNING" if status_code >= 400 else "INFO")
        category = "http"
        async with AsyncSessionLocal() as db:
            db.add(
                AppLog(
                    level=level,
                    category=category,
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    message=f"{request.method} {request.url.path} {status_code} {elapsed_ms}ms",
                    created_at=utcnow(),
                )
            )
            await db.commit()
    return response

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
                    # Persist lightweight audit
                    new_audit = SEOAudit(
                        site_id=site.id,
                        url=audit.url,
                        status_code=audit.status_code,
                        title=audit.title,
                        title_length=audit.title_length,
                        h1=audit.h1,
                        is_indexed=audit.is_indexed,
                        last_check=utcnow()
                    )
                    db.add(new_audit)
                    await db.commit()

                    # Persist full technical audit (scan + robots + sitemap + aggregated metric)
                    await tech_audit_service.run(db, site=site)

                    # Pull webmaster data if configured (best-effort, skips if tokens missing)
                    try:
                        await webmaster_service.fetch_gsc_daily_metrics(db, site)
                        await webmaster_service.fetch_yandex_daily_metrics(db, site)
                    except Exception as e:
                        logger.exception(f"Webmaster fetch error site_id={site.id}: {e}")

                    try:
                        await link_analysis_service.analyze_site(db, site_id=site.id, limit=50)
                    except Exception as e:
                        logger.exception(f"Link analysis error site_id={site.id}: {e}")

                    try:
                        await alert_service.evaluate_and_notify(db, site=site, organization_id=getattr(site, "organization_id", None))
                    except Exception as e:
                        logger.exception(f"Alerts error site_id={site.id}: {e}")
                except Exception as e:
                    logger.error(f"Error checking site {site.domain}: {e}")

        # Sleep for specified interval (default 2h)
        await asyncio.sleep(settings.CHECK_INTERVAL_HOURS * 3600)

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": utcnow()}

# Middleware for simple context (like version)
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
