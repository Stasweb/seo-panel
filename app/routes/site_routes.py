from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.services.site_service import site_service, task_service
from app.services.import_service import import_service
from app.schemas.schemas import SiteCreate, SiteUpdate, Site, TaskCreate, TaskUpdate, Task, CSVImportResponse
from typing import List
from app.services.organization_service import organization_service
from app.services.auto_task_service import auto_task_service

router = APIRouter(prefix="/sites", tags=["sites"])

@router.get("/", response_model=List[Site])
async def list_sites(request: Request, db: AsyncSession = Depends(get_db)):
    """
    List all sites.
    """
    role = getattr(request.state, "role", None) or "viewer"
    if role == "admin":
        return await site_service.get_multi(db)
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    rows = await db.execute(select(site_service.model).where(site_service.model.organization_id == org_id).order_by(site_service.model.id.asc()))
    return rows.scalars().all()

@router.get("/{site_id}", response_model=Site)
async def site_detail(site_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Get site by id.
    """
    site = await site_service.get(db, id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        org_id = getattr(request.state, "organization_id", None)
        if org_id and getattr(site, "organization_id", None) != org_id:
            raise HTTPException(status_code=404, detail="Site not found")
    return site

@router.post("/", response_model=Site, status_code=201)
async def create_site(site_in: SiteCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Create a new site.
    """
    role = getattr(request.state, "role", None) or "viewer"
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        org = await organization_service.ensure_default(db)
        org_id = org.id
    if role != "admin":
        can = await organization_service.can_add_site(db, organization_id=org_id)
        if not can:
            raise HTTPException(status_code=400, detail="План ограничивает количество сайтов")
    payload = site_in.model_dump()
    payload["organization_id"] = org_id
    db_obj = site_service.model(**payload)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

@router.patch("/{site_id}", response_model=Site)
async def update_site(site_id: int, site_in: SiteUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Update an existing site.
    """
    site = await site_service.get(db, id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        org_id = getattr(request.state, "organization_id", None)
        if org_id and getattr(site, "organization_id", None) != org_id:
            raise HTTPException(status_code=404, detail="Site not found")
    return await site_service.update(db, db_obj=site, obj_in=site_in)

@router.delete("/{site_id}", status_code=204)
async def delete_site(site_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Delete site.
    """
    site = await site_service.get(db, id=site_id)
    if not site:
        return Response(status_code=204)
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        org_id = getattr(request.state, "organization_id", None)
        if org_id and getattr(site, "organization_id", None) != org_id:
            raise HTTPException(status_code=404, detail="Site not found")
    await site_service.remove(db, id=site_id)
    return Response(status_code=204)

@router.post("/{site_id}/import", response_model=CSVImportResponse)
async def import_csv(
    site_id: int,
    file: UploadFile = File(...),
    source: str = "gsc",
    db: AsyncSession = Depends(get_db),
):
    """
    Import SEO positions from CSV.
    """
    content = await file.read()
    csv_text = content.decode("utf-8", errors="replace")

    if source == "gsc":
        imported_count = await import_service.import_gsc_csv(db, site_id, csv_text)
    else:
        imported_count = await import_service.import_generic_csv(db, site_id, csv_text)

    return CSVImportResponse(imported_count=imported_count)

@router.get("/{site_id}/tasks", response_model=List[Task])
async def list_tasks(site_id: int, db: AsyncSession = Depends(get_db)):
    """
    List tasks for a site.
    """
    result = await db.execute(select(task_service.model).where(task_service.model.site_id == site_id))
    return result.scalars().all()


@router.post("/{site_id}/auto-tasks/run")
async def run_auto_tasks(site_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    role = getattr(request.state, "role", None) or "viewer"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    site = await db.get(site_service.model, int(site_id))
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await auto_task_service.sync_site(db, site_id=int(site_id), max_tasks=12, include_low=False)

@router.post("/{site_id}/tasks", response_model=Task, status_code=201)
async def create_task(site_id: int, task_in: TaskCreate, db: AsyncSession = Depends(get_db)):
    """
    Create task for a site.
    """
    if task_in.site_id != site_id:
        raise HTTPException(status_code=400, detail="site_id mismatch")
    return await task_service.create(db, obj_in=task_in)

@router.patch("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task_in: TaskUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update task.
    """
    task = await task_service.get(db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return await task_service.update(db, db_obj=task, obj_in=task_in)


@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get task by id.
    """
    task = await task_service.get(db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete task.
    """
    await task_service.remove(db, id=task_id)
    return Response(status_code=204)
