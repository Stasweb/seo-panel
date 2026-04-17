from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Note
from app.utils.time import utcnow


class NoteService:
    def _normalize_color(self, color: Optional[str]) -> str:
        c = (color or "gray").strip().lower()
        if c not in ("gray", "yellow", "green", "red"):
            c = "gray"
        return c

    async def list(self, db: AsyncSession, *, user_id: int, status: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        limit = max(1, min(500, int(limit)))
        q = select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc()).limit(limit)
        if status:
            q = q.where(Note.status == status)
        rows = (await db.execute(q)).scalars().all()
        return [
            {
                "id": n.id,
                "user_id": n.user_id,
                "site_id": n.site_id,
                "title": n.title,
                "content": n.content,
                "status": n.status,
                "color": n.color or "gray",
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ]

    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        site_id: Optional[int],
        title: str,
        content: Optional[str],
        status: str,
        color: Optional[str],
    ) -> Dict[str, Any]:
        title = (title or "").strip()
        if not title:
            raise ValueError("title required")
        status = (status or "todo").strip()
        if status not in ("todo", "in_progress", "done"):
            status = "todo"
        color = self._normalize_color(color)
        n = Note(
            user_id=user_id,
            site_id=site_id,
            title=title,
            content=(content or None),
            status=status,
            color=color,
            created_at=utcnow(),
        )
        db.add(n)
        await db.commit()
        await db.refresh(n)
        return {"id": n.id}

    async def update(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        note_id: int,
        title: Optional[str],
        content: Optional[str],
        status: Optional[str],
        color: Optional[str],
    ) -> Dict[str, Any]:
        n = await db.get(Note, note_id)
        if not n or n.user_id != user_id:
            raise ValueError("not found")
        if title is not None:
            t = title.strip()
            if not t:
                raise ValueError("title required")
            n.title = t
        if content is not None:
            n.content = content
        if status is not None:
            st = status.strip()
            if st not in ("todo", "in_progress", "done"):
                raise ValueError("invalid status")
            n.status = st
        if color is not None:
            n.color = self._normalize_color(color)
        db.add(n)
        await db.commit()
        return {"ok": True}

    async def delete(self, db: AsyncSession, *, user_id: int, note_id: int) -> Dict[str, Any]:
        n = await db.get(Note, note_id)
        if not n or n.user_id != user_id:
            raise ValueError("not found")
        await db.delete(n)
        await db.commit()
        return {"ok": True}


note_service = NoteService()
