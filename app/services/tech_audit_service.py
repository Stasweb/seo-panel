from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Site
from app.services.metrics_service import metrics_service
from app.services.robots_service import robots_service
from app.services.sitemap_service import sitemap_service
from app.services.site_scan_service import site_scan_service
from app.utils.user_agents import resolve_user_agent

logger = logging.getLogger(__name__)


class TechAuditService:
    """
    Runs a full technical audit for a site:
    - status + title length + h1 + response time + indexed + health score (via SiteScanHistory)
    - robots.txt analysis (saved to MetricHistory)
    - sitemap analysis (saved to MetricHistory)
    """

    async def run(
        self,
        db: AsyncSession,
        *,
        site: Site,
        user_agent_choice: Optional[str] = None,
        custom_user_agent: Optional[str] = None,
        respect_robots_txt: bool = True,
        use_sitemap: bool = True,
        pause_ms: int = 0,
    ) -> Dict[str, Any]:
        ua = resolve_user_agent(user_agent_choice, custom_user_agent, settings.USER_AGENT)
        pause_s = max(0.0, float(pause_ms or 0) / 1000.0)

        scan_row = await site_scan_service.scan_site(
            db,
            site,
            user_agent_choice=user_agent_choice,
            custom_user_agent=custom_user_agent,
        )

        if pause_s > 0:
            await asyncio.sleep(pause_s)

        if respect_robots_txt:
            robots = await robots_service.fetch_and_analyze(site.domain, user_agent=ua)
        else:
            robots = {"status": "SKIPPED", "detail": "robots check disabled in site settings"}
        await metrics_service.save(db, site_id=site.id, metric_type="robots", value=robots)

        if pause_s > 0:
            await asyncio.sleep(pause_s)

        if use_sitemap:
            sitemap = await sitemap_service.fetch_and_analyze(site.domain, user_agent=ua)
        else:
            sitemap = {"status": "SKIPPED", "detail": "sitemap check disabled in site settings"}
        await metrics_service.save(db, site_id=site.id, metric_type="sitemap", value=sitemap)

        summary = {
            "site_id": site.id,
            "user_agent_choice": user_agent_choice,
            "scan": {
                "status_code": scan_row.status_code,
                "response_time_ms": scan_row.response_time_ms,
                "title_length": scan_row.title_length,
                "h1_present": scan_row.h1_present,
                "indexed": scan_row.indexed,
                "health_score": scan_row.health_score,
                "created_at": scan_row.created_at.isoformat() if scan_row.created_at else None,
            },
            "robots_status": robots.get("status"),
            "sitemap_status": sitemap.get("status"),
        }
        await metrics_service.save(db, site_id=site.id, metric_type="tech_audit", value=summary)

        return summary


tech_audit_service = TechAuditService()
