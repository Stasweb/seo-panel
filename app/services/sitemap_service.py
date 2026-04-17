from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from app.core.http_client import http_service
from app.core.config import settings

logger = logging.getLogger(__name__)


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_sitemap(xml_text: str) -> Dict[str, Any]:
    """
    Parse sitemap.xml or sitemap_index.xml.
    Supports urlset and sitemapindex.
    """
    root = ET.fromstring(xml_text)
    kind = _strip_ns(root.tag)

    if kind == "sitemapindex":
        sitemaps: List[Dict[str, Any]] = []
        for sm in root.findall(".//{*}sitemap"):
            loc = sm.findtext("{*}loc")
            lastmod = sm.findtext("{*}lastmod")
            if loc:
                sitemaps.append({"loc": loc, "lastmod": lastmod})
        return {"type": "sitemapindex", "sitemaps": sitemaps}

    if kind == "urlset":
        urls: List[Dict[str, Any]] = []
        for u in root.findall(".//{*}url"):
            loc = u.findtext("{*}loc")
            lastmod = u.findtext("{*}lastmod")
            if loc:
                urls.append({"loc": loc, "lastmod": lastmod})
        return {"type": "urlset", "urls": urls}

    return {"type": "unknown", "raw_root": kind}


class SitemapService:
    """
    sitemap analyzer.
    """

    async def fetch_and_analyze(self, domain: str, *, user_agent: str) -> Dict[str, Any]:
        """
        Try /sitemap.xml then /sitemap_index.xml. Parse and return summary.
        """
        if settings.TESTING:
            base = domain.strip()
            if not base.startswith(("http://", "https://")):
                base = f"https://{base}"
            base = base.rstrip("/")
            return {
                "status": "OK",
                "url": f"{base}/sitemap.xml",
                "http_status": 200,
                "errors": [],
                "sitemaps": [],
                "urls_count": 1,
                "lastmod_latest": None,
            }
        base = domain.strip()
        if not base.startswith(("http://", "https://")):
            base = f"https://{base}"
        base = base.rstrip("/")

        candidates = [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml"]

        last_error: Optional[str] = None
        chosen_url: Optional[str] = None
        xml_text: Optional[str] = None
        http_status: Optional[int] = None

        for url in candidates:
            try:
                res = await http_service.get_text(
                    url,
                    user_agent=user_agent,
                    cache_key=f"sitemap:{url}:{user_agent}",
                    timeout=12.0,
                    follow_redirects=True,
                )
                http_status = res.status_code
                if res.status_code != 200:
                    last_error = f"{url}: HTTP {res.status_code}"
                    continue
                chosen_url = url
                xml_text = res.text or ""
                break
            except Exception as e:
                logger.exception(f"sitemap fetch failed url={url}: {e}")
                last_error = f"{url}: ошибка загрузки"
                continue

        if not chosen_url or xml_text is None:
            return {
                "status": "ERROR",
                "url": candidates[0],
                "http_status": http_status,
                "errors": [last_error or "sitemap не найден"],
                "sitemaps": [],
                "urls_count": 0,
                "lastmod_latest": None,
            }

        try:
            parsed = _parse_sitemap(xml_text)
        except Exception:
            return {
                "status": "ERROR",
                "url": chosen_url,
                "http_status": 200,
                "errors": ["Не удалось распарсить XML sitemap."],
                "sitemaps": [],
                "urls_count": 0,
                "lastmod_latest": None,
            }

        if parsed["type"] == "urlset":
            urls = parsed["urls"]
            lastmods = [u.get("lastmod") for u in urls if u.get("lastmod")]
            latest = max(lastmods) if lastmods else None
            return {
                "status": "OK",
                "url": chosen_url,
                "http_status": 200,
                "errors": [],
                "sitemaps": [],
                "urls_count": len(urls),
                "lastmod_latest": latest,
            }

        if parsed["type"] == "sitemapindex":
            sitemaps = parsed["sitemaps"]
            lastmods = [s.get("lastmod") for s in sitemaps if s.get("lastmod")]
            latest = max(lastmods) if lastmods else None
            status = "OK" if sitemaps else "WARNING"
            return {
                "status": status,
                "url": chosen_url,
                "http_status": 200,
                "errors": [],
                "sitemaps": sitemaps,
                "urls_count": None,
                "lastmod_latest": latest,
            }

        return {
            "status": "WARNING",
            "url": chosen_url,
            "http_status": 200,
            "errors": ["Неизвестный формат sitemap."],
            "sitemaps": [],
            "urls_count": 0,
            "lastmod_latest": None,
        }


sitemap_service = SitemapService()
