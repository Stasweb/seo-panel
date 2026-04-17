from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.ai_config_service import ai_config_service
from app.services.ollama_client import ollama_client


class AIRuntimeService:
    async def resolve(self, db: AsyncSession) -> Dict[str, Any]:
        if settings.TESTING:
            return {
                "provider": "auto",
                "model": None,
                "effective_provider": None,
                "effective_model": None,
                "ollama": {"available": False, "models": []},
            }

        cfg = await ai_config_service.get_config(db)
        provider = (cfg.get("provider") or settings.AI_PROVIDER or "auto").strip().lower()
        model = (cfg.get("model") or settings.AI_MODEL or "").strip() or None

        ollama_ok = await ollama_client.is_available()
        models = await ollama_client.list_models() if ollama_ok else []

        if provider in {"off", "none", "disabled"}:
            effective_provider = None
        elif provider == "ollama":
            effective_provider = "ollama" if ollama_ok else None
        else:
            effective_provider = "ollama" if ollama_ok else None

        effective_model = model
        if effective_provider == "ollama":
            if not effective_model or (models and effective_model not in models):
                effective_model = self._pick_default_model(models)
        else:
            effective_model = None

        return {
            "provider": provider,
            "model": model,
            "effective_provider": effective_provider,
            "effective_model": effective_model,
            "ollama": {"available": ollama_ok, "models": models},
        }

    def _pick_default_model(self, models: List[str]) -> Optional[str]:
        if not models:
            return None
        preferred = ["llama3.3", "llama3.2", "llama3.1", "llama3", "qwen2.5", "mistral", "gemma"]
        lower = {m: m.lower() for m in models}
        for p in preferred:
            for m in models:
                if p in lower[m]:
                    return m
        return models[0]


ai_runtime_service = AIRuntimeService()

