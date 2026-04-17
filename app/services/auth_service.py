from __future__ import annotations

from typing import Optional, Tuple

from app.core.config import settings
from app.core.security import verify_password, create_session_cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User


class AuthService:
    """
    Single-admin authentication service based on credentials stored in .env.
    """

    async def verify_credentials(self, db: AsyncSession, *, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Verify provided credentials against DB users first, then ADMIN_* from .env.
        """
        username = (username or "").strip()
        if not username:
            return False, None

        row = (await db.execute(select(User).where(User.username == username, User.is_active == True))).scalars().first()
        if row and verify_password(password, row.password_hash):
            role = (row.role or "viewer").strip().lower()
            if role not in ("admin", "manager", "viewer"):
                role = "viewer"
            return True, role

        if username != settings.ADMIN_USERNAME:
            return False, None
        ok = verify_password(password, settings.ADMIN_PASSWORD_HASH)
        if ok:
            return True, "admin"
        return False, None

    def issue_session(self, username: str, role: str) -> str:
        """
        Issue a signed session cookie for a user.
        """
        return create_session_cookie(username, role=role)


auth_service = AuthService()
