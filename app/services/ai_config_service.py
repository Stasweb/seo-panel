from __future__ import annotations

from typing import Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AppSetting


class AIConfigService:
    async def get_config(self, db: AsyncSession) -> Dict[str, Any]:
        rows = (await db.execute(select(AppSetting).where(AppSetting.key.in_(["ai_provider", "ai_model"])))).scalars().all()
        kv = {r.key: r.value for r in rows}
        return {"provider": kv.get("ai_provider") or None, "model": kv.get("ai_model") or None}

    async def set_config(self, db: AsyncSession, *, provider: Optional[str], model: Optional[str]) -> Dict[str, Any]:
        provider_v = (provider or "").strip().lower() or None
        model_v = (model or "").strip() or None
        await self._upsert(db, "ai_provider", provider_v or "")
        await self._upsert(db, "ai_model", model_v or "")
        await db.commit()
        return {"ok": True, "provider": provider_v, "model": model_v}

    async def _upsert(self, db: AsyncSession, key: str, value: str) -> None:
        row = await db.scalar(select(AppSetting).where(AppSetting.key == key))
        if not row:
            row = AppSetting(key=key, value=value)
            db.add(row)
        else:
            row.value = value
            db.add(row)


ai_config_service = AIConfigService()

