from __future__ import annotations

from typing import Optional, Dict, Any, Tuple

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse, JSONResponse

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.models import User


_pbkdf2_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=settings.SECRET_KEY, salt="session")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify password against bcrypt/passlib hash stored in environment.
    """
    if not password_hash:
        return False
    try:
        ph = str(password_hash)
        if ph.startswith(("$2a$", "$2b$", "$2y$")):
            try:
                import bcrypt  # type: ignore
            except Exception:
                return False
            return bcrypt.checkpw(plain_password.encode("utf-8"), ph.encode("utf-8"))
        if ph.startswith("$pbkdf2-sha256$"):
            return _pbkdf2_context.verify(plain_password, ph)
        return False
    except Exception:
        return False


def create_session_cookie(username: str, role: str) -> str:
    """
    Create a signed session cookie value that can be stored client-side.
    """
    payload = {"u": username, "r": role}
    return _serializer().dumps(payload)


def read_session(cookie_value: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate session cookie and extract username + role.
    """
    try:
        data = _serializer().loads(cookie_value, max_age=settings.SESSION_MAX_AGE_SECONDS)
        if isinstance(data, dict):
            username = data.get("u")
            role = data.get("r")
            if isinstance(username, str) and username:
                return username, role if isinstance(role, str) and role else None
        return None, None
    except (BadSignature, SignatureExpired):
        return None, None
    except Exception:
        return None, None


def is_authenticated(request: Request) -> bool:
    """
    Check if request has a valid authenticated session.
    """
    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not cookie:
        return False
    username, _ = read_session(cookie)
    return username is not None


def get_request_user(request: Request) -> Tuple[Optional[str], Optional[str]]:
    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not cookie:
        return None, None
    return read_session(cookie)


def build_auth_redirect_response() -> Response:
    """
    Build a response for unauthenticated access.
    Prefers HTMX redirect when possible.
    """
    return RedirectResponse(url="/login", status_code=303)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Cookie-based auth middleware.
    Protects /api/* and UI pages (/ and /sites) while allowing /login and static assets.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path.startswith("/static/") or path in ("/health",):
            return await call_next(request)

        if path in ("/login",) or path.startswith("/api/auth/login"):
            return await call_next(request)

        if path in ("/logout",):
            return await call_next(request)

        protected_ui = (
            path in ("/", "/sites", "/links", "/purchased-links", "/users", "/notes", "/keywords", "/logs", "/competitors", "/tasks", "/content-plans")
            or path.startswith("/domain-analysis/")
            or path.startswith("/recommendations/")
        )
        protected_api = path.startswith("/api/")

        if protected_ui or protected_api:
            if not is_authenticated(request):
                if request.headers.get("HX-Request") == "true":
                    return Response(status_code=401, headers={"HX-Redirect": "/login"})
                if protected_api:
                    return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
                return build_auth_redirect_response()

        username, role = get_request_user(request)
        if username:
            if not role:
                role = "admin" if username == settings.ADMIN_USERNAME else "viewer"
            request.state.username = username
            request.state.role = role
            async with AsyncSessionLocal() as db:
                row = (await db.execute(select(User).where(User.username == username))).scalars().first()
                if row:
                    request.state.user_id = row.id
                    request.state.organization_id = row.organization_id
                else:
                    request.state.user_id = None
                    request.state.organization_id = None

        if protected_api:
            role = getattr(request.state, "role", None) or "viewer"
            if path.startswith("/api/users"):
                if role != "admin":
                    return JSONResponse(status_code=403, content={"detail": "Forbidden"})
            elif request.method in ("POST", "PUT", "PATCH", "DELETE"):
                if role not in ("admin", "manager"):
                    return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        if protected_ui and path == "/users":
            role = getattr(request.state, "role", None) or "viewer"
            if role != "admin":
                return build_auth_redirect_response()

        return await call_next(request)
