from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.models import Site, GSCAccount, YandexAccount, KeywordMetrics
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


class WebmasterService:
    """
    Lightweight integrations for Google Search Console and Yandex Webmaster.

    Notes:
    - OAuth flows are intentionally not implemented to keep the server lightweight.
    - This module supports token-based usage: you paste an access token and required IDs.
    - If tokens are not configured, background jobs will skip gracefully.
    """

    async def upsert_gsc_token(self, db: AsyncSession, site_id: int, *, site_url: str, access_token: str) -> GSCAccount:
        row = await db.scalar(select(GSCAccount).where(GSCAccount.site_id == site_id))
        if not row:
            row = GSCAccount(site_id=site_id)
            db.add(row)

        row.site_url = site_url
        row.access_token = access_token
        row.connected = True
        row.updated_at = utcnow()
        await db.commit()
        await db.refresh(row)
        return row

    async def upsert_yandex_token(self, db: AsyncSession, site_id: int, *, host_id: str, oauth_token: str) -> YandexAccount:
        row = await db.scalar(select(YandexAccount).where(YandexAccount.site_id == site_id))
        if not row:
            row = YandexAccount(site_id=site_id)
            db.add(row)

        row.host_id = host_id
        row.oauth_token = oauth_token
        row.connected = True
        row.updated_at = utcnow()
        await db.commit()
        await db.refresh(row)
        return row

    async def _ensure_gsc_access_token(self, db: AsyncSession, *, row: GSCAccount) -> Optional[str]:
        if not row.access_token:
            return None
        if not row.refresh_token or not row.token_expires_at:
            return row.access_token
        if row.token_expires_at > utcnow() + timedelta(seconds=60):
            return row.access_token
        if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
            return row.access_token

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                        "refresh_token": row.refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={"Accept": "application/json"},
                )
                if resp.status_code != 200:
                    logger.warning(f"GSC token refresh failed site_id={row.site_id} status={resp.status_code} body={resp.text[:200]}")
                    return row.access_token
                data = resp.json() or {}
                token = data.get("access_token")
                exp = data.get("expires_in")
                if token:
                    row.access_token = str(token)
                if exp:
                    try:
                        row.token_expires_at = utcnow() + timedelta(seconds=int(exp))
                    except Exception:
                        pass
                row.updated_at = utcnow()
                db.add(row)
                await db.commit()
                return row.access_token
        except Exception as e:
            logger.warning(f"GSC token refresh exception site_id={row.site_id}: {e}")
            return row.access_token

    async def fetch_gsc_daily_metrics(self, db: AsyncSession, site: Site) -> int:
        """
        Fetch daily query metrics from GSC Search Analytics API and store into KeywordMetrics.

        Requires:
        - WebmasterData.gsc_site_url
        - WebmasterData.gsc_access_token (OAuth access token)
        """
        row = await db.scalar(select(GSCAccount).where(GSCAccount.site_id == site.id))
        if not row or not row.connected or not row.site_url or not row.access_token:
            return 0
        token = await self._ensure_gsc_access_token(db, row=row)
        if not token:
            return 0

        site_url_encoded = quote(row.site_url, safe="")
        url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site_url_encoded}/searchAnalytics/query"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "startDate": str(date.today()),
            "endDate": str(date.today()),
            "dimensions": ["query"],
            "rowLimit": 250,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"GSC fetch failed site_id={site.id} status={resp.status_code} body={resp.text[:200]}")
                    return 0
                data = resp.json()
        except Exception as e:
            logger.exception(f"GSC fetch exception site_id={site.id}: {e}")
            return 0

        rows = data.get("rows") or []
        imported = 0
        for r in rows:
            keys = r.get("keys") or []
            keyword = keys[0] if keys else None
            if not keyword:
                continue
            km = KeywordMetrics(
                site_id=site.id,
                keyword=str(keyword),
                clicks=int(r.get("clicks") or 0),
                impressions=int(r.get("impressions") or 0),
                ctr=float(r.get("ctr") or 0.0),
                position=float(r.get("position") or 0.0),
                source="gsc",
                date=date.today(),
                created_at=utcnow(),
            )
            db.add(km)
            imported += 1

        await db.commit()
        return imported

    async def fetch_yandex_daily_metrics(self, db: AsyncSession, site: Site) -> int:
        """
        Fetch daily metrics from Yandex Webmaster API and store into KeywordMetrics.

        Requires:
        - WebmasterData.yandex_host_id
        - WebmasterData.yandex_oauth_token

        This implementation uses a conservative endpoint and stores what is available.
        """
        record = await db.scalar(select(YandexAccount).where(YandexAccount.site_id == site.id))
        if not record or not record.connected or not record.host_id or not record.oauth_token:
            return 0

        headers = {"Authorization": f"OAuth {record.oauth_token}"}

        url = f"https://api.webmaster.yandex.net/v4/hosts/{record.host_id}/search-queries/popular"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Yandex fetch failed site_id={site.id} status={resp.status_code} body={resp.text[:200]}")
                    return 0
                data = resp.json()
        except Exception as e:
            logger.exception(f"Yandex fetch exception site_id={site.id}: {e}")
            return 0

        queries = (data.get("queries") or [])[:250]
        imported = 0
        for q in queries:
            keyword = q.get("query") or q.get("text")
            if not keyword:
                continue
            km = KeywordMetrics(
                site_id=site.id,
                keyword=str(keyword),
                clicks=int(q.get("clicks") or 0),
                impressions=int(q.get("impressions") or 0),
                ctr=float(q.get("ctr") or 0.0),
                position=float(q.get("position") or 0.0),
                source="yandex",
                date=date.today(),
                created_at=utcnow(),
            )
            db.add(km)
            imported += 1

        await db.commit()
        return imported


webmaster_service = WebmasterService()
