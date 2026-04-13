from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.seo_service import seo_service
from typing import Optional

router = APIRouter(prefix="/seo", tags=["seo"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/tools", response_class=HTMLResponse)
async def seo_tools(request: Request):
    """
    SEO tools main page.
    """
    return templates.TemplateResponse("seo/tools.html", {"request": request})

@router.post("/tools/density", response_class=HTMLResponse)
async def keyword_density(
    request: Request,
    text: str = Form(...)
):
    """
    Calculate keyword density (HTMX).
    """
    density = seo_service.calculate_keyword_density(text)
    return templates.TemplateResponse(
        "seo/partials/density_results.html", 
        {"request": request, "density": density}
    )

@router.post("/tools/meta-gen", response_class=HTMLResponse)
async def generate_meta(
    request: Request,
    content: str = Form(...)
):
    """
    Generate meta description (HTMX).
    """
    meta = seo_service.generate_meta_description(content)
    return templates.TemplateResponse(
        "seo/partials/meta_result.html", 
        {"request": request, "meta": meta}
    )

@router.post("/audit/check", response_class=HTMLResponse)
async def audit_url(
    request: Request,
    url: str = Form(...)
):
    """
    Quick audit for a single URL (HTMX).
    """
    result = await seo_service.check_url(url)
    return templates.TemplateResponse(
        "seo/partials/audit_result.html", 
        {"request": request, "result": result}
    )
