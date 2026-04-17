from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Site, MetricHistory, SiteScanHistory
from app.services.email_service import email_service
from app.services.notification_service import notification_service


class AlertService:
    async def evaluate_and_notify(self, db: AsyncSession, *, site: Site, organization_id: Optional[int]) -> None:
        if not getattr(site, "email_alerts_enabled", False) or not getattr(site, "alert_email", None):
            return

        email = str(site.alert_email).strip()
        if not email:
            return

        scan = (await db.execute(
            select(SiteScanHistory)
            .where(SiteScanHistory.site_id == site.id)
            .order_by(SiteScanHistory.created_at.desc())
            .limit(1)
        )).scalars().first()
        if scan and scan.status_code and int(scan.status_code) != 200:
            msg = f"Сайт {site.domain} отвечает HTTP {scan.status_code}"
            await notification_service.create_if_not_recent(
                db,
                organization_id=organization_id,
                site_id=site.id,
                user_id=None,
                event_type="site_down",
                severity="error",
                message=msg,
                dedup_minutes=120,
            )
            await email_service.send_email(to_email=email, subject="SEO Studio: сайт недоступен", body=msg)

        robots = (await db.execute(
            select(MetricHistory)
            .where(MetricHistory.site_id == site.id, MetricHistory.metric_type == "robots")
            .order_by(MetricHistory.created_at.desc())
            .limit(1)
        )).scalars().first()
        if robots:
            st = str((robots.value_json or {}).get("status") or "").upper()
            if st == "ERROR":
                msg = f"robots.txt: ERROR для {site.domain}"
                await notification_service.create_if_not_recent(
                    db,
                    organization_id=organization_id,
                    site_id=site.id,
                    user_id=None,
                    event_type="robots_error",
                    severity="error",
                    message=msg,
                    dedup_minutes=120,
                )
                await email_service.send_email(to_email=email, subject="SEO Studio: robots.txt ошибка", body=msg)

        sitemap = (await db.execute(
            select(MetricHistory)
            .where(MetricHistory.site_id == site.id, MetricHistory.metric_type == "sitemap")
            .order_by(MetricHistory.created_at.desc())
            .limit(1)
        )).scalars().first()
        if sitemap:
            st = str((sitemap.value_json or {}).get("status") or "").upper()
            if st == "ERROR":
                msg = f"sitemap: ERROR для {site.domain}"
                await notification_service.create_if_not_recent(
                    db,
                    organization_id=organization_id,
                    site_id=site.id,
                    user_id=None,
                    event_type="sitemap_error",
                    severity="error",
                    message=msg,
                    dedup_minutes=120,
                )
                await email_service.send_email(to_email=email, subject="SEO Studio: sitemap ошибка", body=msg)

        ahrefs = (await db.execute(
            select(MetricHistory)
            .where(MetricHistory.site_id == site.id, MetricHistory.metric_type == "links_ahrefs")
            .order_by(MetricHistory.created_at.desc())
            .limit(1)
        )).scalars().first()
        if ahrefs:
            tox = float((ahrefs.value_json or {}).get("toxic_pct") or 0)
            if tox >= 20.0:
                msg = f"Рост токсичных ссылок: {tox}% для {site.domain}"
                await notification_service.create_if_not_recent(
                    db,
                    organization_id=organization_id,
                    site_id=site.id,
                    user_id=None,
                    event_type="toxic_growth",
                    severity="warning",
                    message=msg,
                    dedup_minutes=240,
                )
                await email_service.send_email(to_email=email, subject="SEO Studio: токсичные ссылки", body=msg)


alert_service = AlertService()

