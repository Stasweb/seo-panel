from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.user_service import user_service


router = APIRouter(prefix="/users", tags=["users"])


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_users(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    return await user_service.list(db)


@router.post("")
async def create_user(payload: UserCreateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    try:
        return await user_service.create(db, username=payload.username, password=payload.password, role=payload.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}")
async def update_user(user_id: int, payload: UserUpdateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    try:
        return await user_service.update(
            db,
            user_id=user_id,
            username=payload.username,
            password=payload.password,
            role=payload.role,
            is_active=payload.is_active,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "not found":
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=400, detail=msg)


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    try:
        return await user_service.delete(db, user_id=user_id)
    except ValueError as e:
        if str(e) == "not found":
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=400, detail=str(e))

