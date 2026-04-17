from __future__ import annotations

from fastapi import APIRouter, Response, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.auth_service import auth_service
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_request_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate admin user and set signed session cookie.
    """
    ok, role = await auth_service.verify_credentials(db, username=username, password=password)
    if not ok or not role:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    cookie_value = auth_service.issue_session(username=username, role=role)
    response = JSONResponse(content={"ok": True})
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=cookie_value,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return response


@router.get("/me")
async def me(request: Request):
    username, role = get_request_user(request)
    if username and not role:
        role = "admin" if username == settings.ADMIN_USERNAME else "viewer"
    return {"username": username, "role": role}
