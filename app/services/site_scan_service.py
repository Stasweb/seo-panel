from __future__ import annotations

import logging
import time
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.http_client import http_service
from app.models.models import Site, SiteScanHistory, SeoHealthScoreHistory, ContentPlan
from app.services.seo_service import seo_service
from app.utils.user_agents import resolve_user_agent
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


class SiteScanService:
    """
    Full site scan service.

    Goals:
    - run a lightweight check for a single representative URL (home page by default)
    - compute a simple SEO health score (0..100)
    - persist results to SiteScanHistory (+ SeoHealthScoreHistory)
    """

    def __init__(self):
        self.default_user_agent = settings.USER_AGENT

    def _normalize_url(self, domain_or_url: str) -> str:
        """
        Ensure URL has scheme; default to https.
        """
        value = (domain_or_url or "").strip()
        if not value:
            return ""
        if value.startswith(("http://", "https://")):
            return value
        return f"https://{value}"

    def _health_score(
        self,
        *,
        status_code: Optional[int],
        title_length: int,
        h1_present: bool,
        indexed: Optional[bool],
        response_time_ms: Optional[int],
    ) -> int:
        """
        Simple deterministic SEO health score.

        Scoring (0..100):
        - status: 60 points max
        - title length: 15 points max
        - h1 presence: 10 points max
        - indexed: 10 points max
        - response time: 5 points max
        """
        score = 0

        if status_code == 200:
            score += 60
        elif status_code and 200 <= status_code < 400:
            score += 45
        elif status_code and 400 <= status_code < 500:
            score += 20
        else:
            score += 0

        if 30 <= title_length <= 65:
            score += 15
        elif 15 <= title_length < 30 or 65 < title_length <= 90:
            score += 8
        else:
            score += 2 if title_length > 0 else 0

        score += 10 if h1_present else 0

        if indexed is True:
            score += 10
        elif indexed is None:
            score += 5
        else:
            score += 0

        if response_time_ms is None:
            score += 0
        elif response_time_ms <= 400:
            score += 5
        elif response_time_ms <= 900:
            score += 3
        elif response_time_ms <= 1500:
            score += 1
        else:
            score += 0

        return max(0, min(100, int(score)))

    async def scan_site(
        self,
        db: AsyncSession,
        site: Site,
        *,
        user_agent_choice: Optional[str] = None,
        custom_user_agent: Optional[str] = None,
    ) -> SiteScanHistory:
        """
        Run scan and persist result for a site.
        """
        url = self._normalize_url(site.domain)
        started = time.perf_counter()

        status_code: Optional[int] = None
        title_length = 0
        h1_present = False
        indexed: Optional[bool] = None
        ua = resolve_user_agent(user_agent_choice, custom_user_agent, self.default_user_agent)

        try:
            indexed = await seo_service.check_indexed(site.domain, user_agent=ua, probe=user_agent_choice)
        except Exception:
            indexed = None

        res = None
        urls = [url]
        if url.startswith("https://"):
            urls.append("http://" + url[len("https://") :])

        try:
            last_exc: Optional[Exception] = None
            for u in urls:
                try:
                    res = await http_service.get_text(
                        u,
                        user_agent=ua,
                        cache_key=f"scan:{u}:{ua}",
                        timeout=10.0,
                        follow_redirects=True,
                    )
                    break
                except Exception as e:
                    last_exc = e
                    continue
            if res is None and last_exc is not None:
                raise last_exc

            status_code = res.status_code if res is not None else None
            html = (res.text or "") if res is not None else ""

            soup = BeautifulSoup(html, "lxml")
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            title_length = len(title)
            h1_present = soup.find("h1") is not None

            if indexed is None and status_code and 200 <= int(status_code) < 400 and res is not None:
                noindex = False
                try:
                    xrt = (res.headers.get("x-robots-tag") or "").lower()
                    meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
                    meta_content = ((meta.get("content") if meta else "") or "").lower()
                    noindex = ("noindex" in xrt) or ("noindex" in meta_content)
                except Exception:
                    noindex = False
                indexed = False if noindex else True
        except Exception as e:
            logger.exception(f"Site scan failed for site_id={site.id} domain={site.domain}: {e}")
            if indexed is None and status_code and 200 <= int(status_code) < 400:
                indexed = True

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        score = self._health_score(
            status_code=status_code,
            title_length=title_length,
            h1_present=h1_present,
            indexed=indexed,
            response_time_ms=elapsed_ms,
        )

        history = SiteScanHistory(
            site_id=site.id,
            status_code=status_code,
            response_time_ms=elapsed_ms,
            title_length=title_length,
            h1_present=h1_present,
            indexed=indexed,
            health_score=score,
            created_at=utcnow(),
        )
        db.add(history)

        db.add(
            SeoHealthScoreHistory(
                site_id=site.id,
                score=score,
                created_at=utcnow(),
            )
        )

        idea_title: Optional[str] = None
        if not h1_present:
            idea_title = f"Добавить H1 на {site.domain}"
        elif title_length > 65:
            idea_title = f"Сократить Title на {site.domain}"
        elif indexed is False:
            idea_title = f"Проверить индексацию {site.domain}"

        if idea_title:
            since = utcnow() - timedelta(days=2)
            existing = (await db.execute(
                select(ContentPlan.id).where(
                    ContentPlan.site_id == site.id,
                    ContentPlan.title == idea_title,
                    ContentPlan.created_at >= since,
                ).limit(1)
            )).first()
            if not existing:
                db.add(ContentPlan(site_id=site.id, title=idea_title, url=url, status="idea", created_at=utcnow()))

        await db.commit()
        await db.refresh(history)
        return history


site_scan_service = SiteScanService()
