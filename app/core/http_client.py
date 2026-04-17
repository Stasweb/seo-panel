from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import httpx

from app.core.config import settings


@dataclass
class CachedValue:
    expires_at: float
    value: "HttpResult"


@dataclass
class HttpResult:
    url: str
    status_code: int
    text: str
    history_count: int


class TTLCache:
    def __init__(self):
        self._items: Dict[str, CachedValue] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[HttpResult]:
        now = time.time()
        async with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            if item.expires_at <= now:
                self._items.pop(key, None)
                return None
            return item.value

    async def set(self, key: str, value: HttpResult, ttl_seconds: int) -> None:
        async with self._lock:
            self._items[key] = CachedValue(expires_at=time.time() + float(ttl_seconds), value=value)


class HttpService:
    def __init__(self):
        self._sem = asyncio.Semaphore(int(settings.HTTP_CONCURRENCY))
        self._cache = TTLCache()

    async def get_text(
        self,
        url: str,
        *,
        user_agent: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        cache_key: Optional[str] = None,
        timeout: float = 12.0,
        follow_redirects: bool = True,
    ) -> HttpResult:
        ttl = int(ttl_seconds if ttl_seconds is not None else settings.HTTP_CACHE_TTL_SECONDS)
        if cache_key and ttl > 0:
            cached = await self._cache.get(cache_key)
            if cached:
                return cached

        headers = {"User-Agent": user_agent or settings.USER_AGENT}
        async with self._sem:
            async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=follow_redirects) as client:
                resp = await client.get(url)
                result = HttpResult(
                    url=str(resp.url),
                    status_code=int(resp.status_code),
                    text=resp.text,
                    history_count=len(resp.history) if resp.history is not None else 0,
                )

        if cache_key and ttl > 0 and 200 <= result.status_code < 400:
            await self._cache.set(cache_key, result, ttl_seconds=ttl)
        return result


http_service = HttpService()

