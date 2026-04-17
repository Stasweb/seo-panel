from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.http_client import http_service
from app.core.config import settings

logger = logging.getLogger(__name__)


def _parse_robots(content: str) -> Dict[str, Any]:
    """
    Minimal robots.txt parser.
    Extracts groups with user-agent + allow/disallow rules and sitemap lines.
    """
    groups: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {"user_agents": [], "allow": [], "disallow": []}
    sitemaps: List[str] = []

    for raw in (content or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = [x.strip() for x in line.split(":", 1)]
        k = key.lower()

        if k == "user-agent":
            if current["user_agents"] and (current["allow"] or current["disallow"]):
                groups.append(current)
                current = {"user_agents": [], "allow": [], "disallow": []}
            current["user_agents"].append(value)
        elif k == "allow":
            current["allow"].append(value)
        elif k == "disallow":
            current["disallow"].append(value)
        elif k == "sitemap":
            sitemaps.append(value)

    if current["user_agents"] and (current["allow"] or current["disallow"]):
        groups.append(current)

    return {"groups": groups, "sitemaps": sitemaps}


def _evaluate_robots(parsed: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Returns (status, warnings).

    Status: OK | WARNING | ERROR
    """
    warnings: List[str] = []
    status = "OK"

    groups = parsed.get("groups") or []
    sitemaps = parsed.get("sitemaps") or []

    if not groups:
        warnings.append("robots.txt без правил (User-agent/Allow/Disallow).")
        status = "WARNING"

    if not sitemaps:
        warnings.append("В robots.txt не найдено Sitemap.")
        status = "WARNING" if status != "ERROR" else status

    for g in groups:
        uas = [ua.strip().lower() for ua in (g.get("user_agents") or [])]
        dis = [d.strip() for d in (g.get("disallow") or [])]
        if "*" in uas and "/" in dis:
            warnings.append("Обнаружен Disallow: / для User-agent: * (сайт закрыт для индексации).")
            status = "ERROR"

    return status, warnings


class RobotsService:
    """
    robots.txt analyzer.
    """

    async def fetch_and_analyze(self, domain: str, *, user_agent: str) -> Dict[str, Any]:
        """
        Download https://{domain}/robots.txt and analyze it.
        """
        if settings.TESTING:
            base = domain.strip()
            if not base.startswith(("http://", "https://")):
                base = f"https://{base}"
            url = base.rstrip("/") + "/robots.txt"
            return {"status": "OK", "url": url, "http_status": 200, "warnings": [], "groups": [], "sitemaps": []}
        url = domain.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        url = url.rstrip("/") + "/robots.txt"

        try:
            res = await http_service.get_text(
                url,
                user_agent=user_agent,
                cache_key=f"robots:{url}:{user_agent}",
                timeout=10.0,
                follow_redirects=True,
            )
            if res.status_code != 200:
                return {
                    "status": "ERROR",
                    "url": url,
                    "http_status": res.status_code,
                    "warnings": [f"robots.txt недоступен (HTTP {res.status_code})."],
                    "groups": [],
                    "sitemaps": [],
                }
            content = res.text or ""
        except Exception as e:
            logger.exception(f"robots fetch failed url={url}: {e}")
            return {
                "status": "ERROR",
                "url": url,
                "http_status": None,
                "warnings": ["Не удалось загрузить robots.txt (ошибка сети/таймаут)."],
                "groups": [],
                "sitemaps": [],
            }

        parsed = _parse_robots(content)
        status, warnings = _evaluate_robots(parsed)
        return {
            "status": status,
            "url": url,
            "http_status": 200,
            "warnings": warnings,
            "groups": parsed["groups"],
            "sitemaps": parsed["sitemaps"],
        }


robots_service = RobotsService()
