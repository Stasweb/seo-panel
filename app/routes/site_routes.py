from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.site_service import site_service
from app.services.import_service import import_service
from app.schemas.schemas import SiteCreate, SiteUpdate
from typing import List, Optional

router = APIRouter(prefix="/sites", tags=["sites"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_sites(request: Request, db: AsyncSession = Depends(get_db)):
    """
    List all sites (HTML page).
    """
    sites = await site_service.get_multi(db)
    return templates.TemplateResponse(
        "sites/list.html",
        {"request": request, "sites": sites}
    )

@router.get("/{site_id}", response_class=HTMLResponse)
async def site_detail(site_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Get site detail (HTML page).
    """
    site = await site_service.get(db, id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    stats = await site_service.get_stats(db, site_id)
    return templates.TemplateResponse(
        "sites/detail.html",
        {"request": request, "site": site, "stats": stats}
    )

@router.post("/create", response_class=HTMLResponse)
async def create_site(
    request: Request,
    domain: str = Form(...),
    cms: Optional[str] = Form(None),
    region: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new site (HTMX request).
    """
    site_in = SiteCreate(domain=domain, cms=cms, region=region, notes=notes)
    await site_service.create(db, obj_in=site_in)

    # Return updated list of sites for HTMX swap
    sites = await site_service.get_multi(db)
    return templates.TemplateResponse(
        "sites/partials/site_list_items.html",
        {"request": request, "sites": sites}
    )

@router.delete("/{site_id}", response_class=HTMLResponse)
async def delete_site(site_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Delete site (HTMX request).
    """
    await site_service.remove(db, id=site_id)
    return "" # HTMX will remove the element if we return empty response with swap

@router.post("/{site_id}/import", response_class=RedirectResponse)
async def import_csv(
    site_id: int,
    file: UploadFile = File(...),
    source: str = Form("gsc"), # gsc or manual
    db: AsyncSession = Depends(get_db)
):
    """
    Import SEO positions from CSV.
    """
    content = await file.read()
    csv_text = content.decode('utf-8')

    if source == "gsc":
        await import_service.import_gsc_csv(db, site_id, csv_text)
    else:
        await import_service.import_generic_csv(db, site_id, csv_text)

    return RedirectResponse(url=f"/sites/{site_id}", status_code=303)
