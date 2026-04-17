from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.services.organization_service import organization_service
from app.utils.time import utcnow


class UserService:
    async def list(self, db: AsyncSession) -> List[Dict[str, Any]]:
        rows = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ]

    async def create(self, db: AsyncSession, *, username: str, password: str, role: str) -> Dict[str, Any]:
        username = (username or "").strip()
        if not username:
            raise ValueError("username required")
        role = (role or "viewer").strip().lower()
        if role not in ("admin", "manager", "viewer"):
            role = "viewer"
        if not password or len(password) < 4:
            raise ValueError("password too short")

        exists = (await db.execute(select(User).where(User.username == username))).scalars().first()
        if exists:
            raise ValueError("username exists")

        org = await organization_service.ensure_default(db)
        try:
            import bcrypt  # type: ignore
        except Exception:
            raise ValueError("bcrypt not installed")
        u = User(
            username=username,
            password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            role=role,
            is_active=True,
            created_at=utcnow(),
            organization_id=org.id,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)
        return {"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat()}

    async def update(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        u = await db.get(User, user_id)
        if not u:
            raise ValueError("not found")
        if username is not None:
            username = username.strip()
            if not username:
                raise ValueError("username required")
            if username != u.username:
                exists = (await db.execute(select(User).where(User.username == username))).scalars().first()
                if exists:
                    raise ValueError("username exists")
                u.username = username
        if password is not None and password != "":
            if len(password) < 4:
                raise ValueError("password too short")
            try:
                import bcrypt  # type: ignore
            except Exception:
                raise ValueError("bcrypt not installed")
            u.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        if role is not None:
            role = role.strip().lower()
            if role not in ("admin", "manager", "viewer"):
                raise ValueError("invalid role")
            u.role = role
        if is_active is not None:
            u.is_active = bool(is_active)

        db.add(u)
        await db.commit()
        await db.refresh(u)
        return {"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat() if u.created_at else None}

    async def delete(self, db: AsyncSession, *, user_id: int) -> Dict[str, Any]:
        u = await db.get(User, user_id)
        if not u:
            raise ValueError("not found")
        await db.delete(u)
        await db.commit()
        return {"ok": True}


user_service = UserService()
