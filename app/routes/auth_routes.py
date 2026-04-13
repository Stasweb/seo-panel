from __future__ import annotations

from fastapi import APIRouter, Response, Form, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.auth_service import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Authenticate admin user and set signed session cookie.
    """
    ok = auth_service.verify_credentials(username=username, password=password)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    cookie_value = auth_service.issue_session(username=username)
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
