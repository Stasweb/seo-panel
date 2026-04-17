from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.note_service import note_service


router = APIRouter(prefix="/notes", tags=["notes"])


class NoteCreateRequest(BaseModel):
    site_id: Optional[int] = None
    title: str
    content: Optional[str] = None
    status: str = "todo"
    color: Optional[str] = "gray"


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    color: Optional[str] = None


@router.get("")
async def list_notes(
    request: Request,
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return []
    return await note_service.list(db, user_id=user_id, status=status)


@router.post("")
async def create_note(payload: NoteCreateRequest, request: Request, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await note_service.create(
            db,
            user_id=user_id,
            site_id=payload.site_id,
            title=payload.title,
            content=payload.content,
            status=payload.status,
            color=payload.color,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{note_id}")
async def update_note(note_id: int, payload: NoteUpdateRequest, request: Request, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await note_service.update(
            db,
            user_id=user_id,
            note_id=note_id,
            title=payload.title,
            content=payload.content,
            status=payload.status,
            color=payload.color,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "not found":
            raise HTTPException(status_code=404, detail="Not found")
        raise HTTPException(status_code=400, detail=msg)


@router.delete("/{note_id}")
async def delete_note(note_id: int, request: Request, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await note_service.delete(db, user_id=user_id, note_id=note_id)
    except ValueError as e:
        msg = str(e)
        if msg == "not found":
            raise HTTPException(status_code=404, detail="Not found")
        raise HTTPException(status_code=400, detail=msg)
