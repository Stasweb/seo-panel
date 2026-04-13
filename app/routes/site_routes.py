from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.services.site_service import site_service, task_service
from app.services.import_service import import_service
from app.schemas.schemas import SiteCreate, SiteUpdate, Site, TaskCreate, TaskUpdate, Task, CSVImportResponse
from typing import List

router = APIRouter(prefix="/sites", tags=["sites"])

@router.get("/", response_model=List[Site])
async def list_sites(db: AsyncSession = Depends(get_db)):
    """
    List all sites.
    """
    return await site_service.get_multi(db)

@router.get("/{site_id}", response_model=Site)
async def site_detail(site_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get site by id.
    """
    site = await site_service.get(db, id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site

@router.post("/", response_model=Site, status_code=201)
async def create_site(site_in: SiteCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new site.
    """
    return await site_service.create(db, obj_in=site_in)

@router.patch("/{site_id}", response_model=Site)
async def update_site(site_id: int, site_in: SiteUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing site.
    """
    site = await site_service.get(db, id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await site_service.update(db, db_obj=site, obj_in=site_in)

@router.delete("/{site_id}", status_code=204)
async def delete_site(site_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete site.
    """
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

@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete task.
    """
    await task_service.remove(db, id=task_id)
    return Response(status_code=204)
