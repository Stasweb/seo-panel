from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.core.http_client import http_service
from app.core.config import settings
from app.services.robots_service import robots_service
from app.services.sitemap_service import sitemap_service


def _normalize_domain(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if v.startswith(("http://", "https://")):
        try:
            p = urlparse(v)
            return (p.netloc or "").lower()
        except Exception:
            return v.lower()
    return v.lower().rstrip("/")

def _issue(priority: str, title: str, what_to_do: str) -> Dict[str, str]:
    return {"priority": priority, "title": title, "what_to_do": what_to_do}


class CompetitorService:
    async def analyze(self, *, domain: str) -> Dict[str, Any]:
        dom = _normalize_domain(domain)
        if not dom:
            return {"ok": False, "detail": "empty domain"}

        if settings.TESTING:
            return {
                "ok": True,
                "domain": dom,
                "url": f"https://{dom}",
                "http_status": 200,
                "title": "TEST",
                "h1": "TEST",
                "meta_description": "TEST",
                "canonical": f"https://{dom}/",
                "robots": {"status": "OK"},
                "sitemap": {"status": "OK"},
                "structure": {"title_length": 4, "h1_present": True, "meta_description_length": 4, "canonical_present": True, "outgoing_links": 1},
                "issues": [],
            }

        url = f"https://{dom}"
        page = await http_service.get_text(url, cache_key=f"competitor_home:{dom}", timeout=12.0, follow_redirects=True)

        title: Optional[str] = None
        h1: Optional[str] = None
        meta_description: Optional[str] = None
        canonical: Optional[str] = None
        outgoing_links = 0

        if page.text:
            soup = BeautifulSoup(page.text, "lxml")
            t = soup.title.string if soup.title and soup.title.string else None
            title = t.strip() if t else None
            h1_tag = soup.find("h1")
            h1 = h1_tag.get_text(" ", strip=True) if h1_tag else None
            md = soup.find("meta", attrs={"name": "description"})
            meta_description = (md.get("content") or "").strip() if md else None
            canon = soup.find("link", attrs={"rel": "canonical"})
            canonical = (canon.get("href") or "").strip() if canon else None
            outgoing_links = len(soup.find_all("a"))

        robots = await robots_service.fetch_and_analyze(dom, user_agent="Mozilla/5.0")
        sitemap = await sitemap_service.fetch_and_analyze(dom, user_agent="Mozilla/5.0")

        structure = {
            "title_length": len(title) if title else 0,
            "h1_present": bool(h1),
            "meta_description_length": len(meta_description) if meta_description else 0,
            "canonical_present": bool(canonical),
            "outgoing_links": outgoing_links,
        }

        issues = []
        if page.status_code != 200:
            issues.append(_issue("high", f"HTTP {page.status_code}", "Проверьте доступность и редиректы на главной странице."))
        if not structure["h1_present"]:
            issues.append(_issue("high", "Нет H1", "Добавьте один H1 на главной странице с основным запросом."))
        if structure["title_length"] > 65:
            issues.append(_issue("medium", "Длинный Title", "Сократите title до ~50–60 символов."))
        if structure["meta_description_length"] == 0:
            issues.append(_issue("medium", "Нет meta description", "Добавьте meta description (120–160 символов)."))
        if robots.get("status") == "ERROR":
            issues.append(_issue("high", "robots.txt ошибка", "Проверьте доступность robots.txt и правила User-agent:*"))
        if sitemap.get("status") == "ERROR":
            issues.append(_issue("high", "sitemap недоступен", "Проверьте /sitemap.xml или /sitemap_index.xml и валидность XML."))
        if outgoing_links >= 200:
            issues.append(_issue("low", "Много исходящих ссылок", "Проверьте, не является ли страница списком/линкопомойкой."))

        return {
            "ok": True,
            "domain": dom,
            "url": page.url,
            "http_status": page.status_code,
            "title": title,
            "h1": h1,
            "meta_description": meta_description,
            "canonical": canonical,
            "robots": robots,
            "sitemap": sitemap,
            "structure": structure,
            "issues": issues,
        }


competitor_service = CompetitorService()
