from __future__ import annotations

from typing import Optional, Dict, Any

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse, JSONResponse

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=settings.SECRET_KEY, salt="session")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify password against bcrypt/passlib hash stored in environment.
    """
    if not password_hash:
        return False
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


def create_session_cookie(username: str) -> str:
    """
    Create a signed session cookie value that can be stored client-side.
    """
    payload = {"u": username}
    return _serializer().dumps(payload)


def read_session_username(cookie_value: str) -> Optional[str]:
    """
    Validate session cookie and extract username.
    """
    try:
        data = _serializer().loads(cookie_value, max_age=settings.SESSION_MAX_AGE_SECONDS)
        if isinstance(data, dict):
            username = data.get("u")
            if isinstance(username, str) and username:
                return username
        return None
    except (BadSignature, SignatureExpired):
        return None
    except Exception:
        return None


def is_authenticated(request: Request) -> bool:
    """
    Check if request has a valid authenticated session.
    """
    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not cookie:
        return False
    return read_session_username(cookie) is not None


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

        protected_ui = path in ("/", "/sites")
        protected_api = path.startswith("/api/")

        if protected_ui or protected_api:
            if not is_authenticated(request):
                if request.headers.get("HX-Request") == "true":
                    return Response(status_code=401, headers={"HX-Redirect": "/login"})
                if protected_api:
                    return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
                return build_auth_redirect_response()

        return await call_next(request)
