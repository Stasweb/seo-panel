from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings


class OllamaClient:
    def __init__(self) -> None:
        self._cached_at: float = 0.0
        self._cached_models: List[str] = []
        self._cached_ok: Optional[bool] = None

    async def is_available(self) -> bool:
        now = time.time()
        if self._cached_ok is not None and (now - self._cached_at) < 15:
            return bool(self._cached_ok)
        try:
            async with httpx.AsyncClient(timeout=0.6) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            ok = resp.status_code == 200
        except Exception:
            ok = False
        self._cached_ok = ok
        self._cached_at = now
        return ok

    async def list_models(self, *, force: bool = False) -> List[str]:
        now = time.time()
        if (not force) and self._cached_models and (now - self._cached_at) < 60:
            return list(self._cached_models)
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
        if resp.status_code != 200:
            return []
        data = resp.json()
        models = data.get("models") or []
        names = []
        for m in models:
            n = (m or {}).get("name")
            if n:
                names.append(str(n))
        names = sorted(set(names))
        self._cached_models = names
        self._cached_at = now
        self._cached_ok = True
        return list(names)

    async def chat_json(self, *, model: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        base = settings.OLLAMA_BASE_URL.rstrip("/")
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": float(temperature)},
        }
        async with httpx.AsyncClient(timeout=float(settings.AI_TIMEOUT_SECONDS)) as client:
            resp = await client.post(f"{base}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        msg = (data or {}).get("message") or {}
        return str(msg.get("content") or "")


ollama_client = OllamaClient()

