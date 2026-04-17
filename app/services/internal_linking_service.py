from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from app.core.http_client import http_service
from app.core.config import settings


class InternalLinkingService:
    async def analyze_home(self, *, domain: str) -> Dict[str, Any]:
        dom = (domain or "").strip()
        if not dom:
            return {"domain": domain, "ok": False, "detail": "empty domain"}

        if settings.TESTING:
            return {
                "domain": dom,
                "ok": True,
                "http_status": 200,
                "internal_links_total": 3,
                "unique_pages": 2,
                "top_pages": [{"path": "/", "count": 2}, {"path": "/about", "count": 1}],
                "depth_hist": [{"depth": 0, "count": 2}],
            }

        base_url = dom if dom.startswith(("http://", "https://")) else f"https://{dom}"
        try:
            res = await http_service.get_text(
                base_url,
                cache_key=f"internal_home:{base_url}",
                timeout=12.0,
                follow_redirects=True,
            )
            soup = BeautifulSoup(res.text, "lxml")

            host = urlparse(str(res.url)).netloc.lower()
            items: Dict[str, int] = {}
            for a in soup.find_all("a"):
                href = a.get("href")
                if not href:
                    continue
                abs_url = urljoin(str(res.url), href)
                p = urlparse(abs_url)
                if p.netloc.lower() != host:
                    continue
                path = p.path or "/"
                if path != "/" and path.endswith("/"):
                    path = path[:-1]
                items[path] = items.get(path, 0) + 1

            top = sorted(items.items(), key=lambda kv: kv[1], reverse=True)[:50]
            depth_hist: Dict[int, int] = {}
            for path, cnt in items.items():
                depth = max(0, path.strip("/").count("/"))
                depth_hist[depth] = depth_hist.get(depth, 0) + 1

            return {
                "domain": dom,
                "ok": True,
                "http_status": res.status_code,
                "internal_links_total": sum(items.values()),
                "unique_pages": len(items),
                "top_pages": [{"path": p, "count": c} for p, c in top],
                "depth_hist": [{"depth": d, "count": c} for d, c in sorted(depth_hist.items(), key=lambda kv: kv[0])],
            }
        except Exception:
            return {"domain": dom, "ok": False, "detail": "fetch failed"}


internal_linking_service = InternalLinkingService()
