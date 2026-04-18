from __future__ import annotations

from typing import Optional, Dict, Any, Tuple
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.http_client import http_service


class PositionCheckService:
    async def check_ddg(self, *, keyword: str, domain: str, limit: int = 50) -> Tuple[Optional[float], Optional[str]]:
        kw = (keyword or "").strip()
        dom = (domain or "").strip().lower().lstrip(".")
        if dom.startswith(("http://", "https://")):
            dom = urlparse(dom).netloc.lower()
        if not kw or not dom:
            return None, None
        if settings.TESTING:
            return 7.0, f"https://{dom}/"

        q = quote_plus(f"{kw} site:{dom}")
        url = f"https://duckduckgo.com/html/?q={q}"
        html = await http_service.get_text(
            url,
            user_agent=settings.USER_AGENT,
            cache_key=f"ddg_serp:{dom}:{kw}",
            timeout=12.0,
            follow_redirects=True,
        )
        soup = BeautifulSoup(html or "", "lxml")
        links = soup.select("a.result__a")
        pos = 0
        for a in links[: max(1, min(100, int(limit)))]:
            href = (a.get("href") or "").strip()
            if not href:
                continue
            real = self._unwrap_ddg(href) or href
            try:
                p = urlparse(real)
                host = (p.netloc or "").lower()
            except Exception:
                host = ""
            pos += 1
            if host == dom or host.endswith("." + dom):
                return float(pos), real
        if pos:
            return 100.0, None
        return None, None

    def _unwrap_ddg(self, href: str) -> Optional[str]:
        try:
            p = urlparse(href)
            qs = parse_qs(p.query or "")
            uddg = (qs.get("uddg") or [None])[0]
            if uddg:
                return unquote(uddg)
        except Exception:
            return None
        return None


position_check_service = PositionCheckService()

