from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import MetricHistory
from app.utils.time import utcnow


class MetricsService:
    """
    Persists generic audit/analysis metrics into MetricHistory.
    """

    async def save(self, db: AsyncSession, *, site_id: int, metric_type: str, value: Dict[str, Any]) -> MetricHistory:
        """
        Save a metric snapshot.
        """
        row = MetricHistory(
            site_id=site_id,
            metric_type=metric_type,
            value_json=value,
            created_at=utcnow(),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


metrics_service = MetricsService()
