from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.security import verify_password, create_session_cookie


class AuthService:
    """
    Single-admin authentication service based on credentials stored in .env.
    """

    def verify_credentials(self, username: str, password: str) -> bool:
        """
        Verify provided credentials against ADMIN_USERNAME and ADMIN_PASSWORD_HASH.
        """
        if username != settings.ADMIN_USERNAME:
            return False
        return verify_password(password, settings.ADMIN_PASSWORD_HASH)

    def issue_session(self, username: str) -> str:
        """
        Issue a signed session cookie for a user.
        """
        return create_session_cookie(username)


auth_service = AuthService()
