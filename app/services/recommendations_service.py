from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Site, SiteScanHistory, MetricHistory
from app.services.ai_runtime_service import ai_runtime_service
from app.services.ai_service import ai_service


class RecommendationsService:
    async def generate(self, db: AsyncSession, *, site_id: int, use_ai: bool = True) -> Dict[str, Any]:
        site = await db.get(Site, site_id)
        if not site:
            return {"site_id": site_id, "items": []}

        items: List[Dict[str, Any]] = []

        scan = (await db.execute(
            select(SiteScanHistory).where(SiteScanHistory.site_id == site_id).order_by(SiteScanHistory.created_at.desc()).limit(1)
        )).scalars().first()
        if scan:
            if scan.h1_present is False:
                items.append(
                    {
                        "priority": "high",
                        "title": "Отсутствует H1",
                        "what_to_do": "Добавьте один H1 на главную страницу и убедитесь, что он содержит основной запрос.",
                    }
                )
            if scan.title_length and int(scan.title_length) > 65:
                items.append(
                    {
                        "priority": "medium",
                        "title": "Слишком длинный title",
                        "what_to_do": "Сократите title до ~50–60 символов и сделайте его уникальным.",
                    }
                )
            if scan.status_code and int(scan.status_code) != 200:
                items.append(
                    {
                        "priority": "high",
                        "title": f"Сайт отвечает HTTP {scan.status_code}",
                        "what_to_do": "Проверьте хостинг/SSL/редиректы. Цель: стабильный HTTP 200.",
                    }
                )
            if scan.indexed is False:
                items.append(
                    {
                        "priority": "high",
                        "title": "Есть сигнал, что сайт не в индексе",
                        "what_to_do": "Проверьте robots, sitemap, мета robots/noindex и доступность страниц для ботов.",
                    }
                )

        robots = (await db.execute(
            select(MetricHistory).where(MetricHistory.site_id == site_id, MetricHistory.metric_type == "robots").order_by(MetricHistory.created_at.desc()).limit(1)
        )).scalars().first()
        if not robots:
            items.append(
                {
                    "priority": "high",
                    "title": "Нет данных по robots.txt",
                    "what_to_do": "Запустите тех. аудит и убедитесь, что robots.txt доступен.",
                }
            )
        else:
            st = str((robots.value_json or {}).get("status") or "").upper()
            if st == "ERROR":
                items.append(
                    {
                        "priority": "high",
                        "title": "robots.txt в ошибке",
                        "what_to_do": "Проверьте доступность robots.txt и отсутствие Disallow: / для User-agent:*.",
                    }
                )
            elif st == "WARNING":
                items.append(
                    {
                        "priority": "medium",
                        "title": "robots.txt требует внимания",
                        "what_to_do": "Добавьте Sitemap в robots.txt и проверьте корректность правил.",
                    }
                )

        sitemap = (await db.execute(
            select(MetricHistory).where(MetricHistory.site_id == site_id, MetricHistory.metric_type == "sitemap").order_by(MetricHistory.created_at.desc()).limit(1)
        )).scalars().first()
        if not sitemap:
            items.append(
                {
                    "priority": "high",
                    "title": "Нет данных по sitemap",
                    "what_to_do": "Разместите sitemap.xml и убедитесь, что он отдаёт HTTP 200 и валиден.",
                }
            )
        else:
            st = str((sitemap.value_json or {}).get("status") or "").upper()
            if st == "ERROR":
                items.append(
                    {
                        "priority": "high",
                        "title": "sitemap недоступен",
                        "what_to_do": "Проверьте /sitemap.xml или /sitemap_index.xml, доступность и корректный XML.",
                    }
                )
            errs = (sitemap.value_json or {}).get("errors") or []
            if isinstance(errs, list) and len(errs) > 0:
                items.append(
                    {
                        "priority": "medium",
                        "title": f"Ошибки в sitemap: {len(errs)}",
                        "what_to_do": "Проверьте дочерние sitemap и HTTP статусы.",
                    }
                )

        ahrefs = (await db.execute(
            select(MetricHistory).where(MetricHistory.site_id == site_id, MetricHistory.metric_type == "links_ahrefs").order_by(MetricHistory.created_at.desc()).limit(1)
        )).scalars().first()
        if ahrefs:
            tox = float((ahrefs.value_json or {}).get("toxic_pct") or 0)
            if tox >= 20.0:
                items.append(
                    {
                        "priority": "high",
                        "title": f"Высокая доля токсичных ссылок: {tox}%",
                        "what_to_do": "Проверьте ссылки с toxic флагом и удалите/дизавоу самые плохие доноры.",
                    }
                )
            elif tox >= 10.0:
                items.append(
                    {
                        "priority": "medium",
                        "title": f"Токсичные ссылки: {tox}%",
                        "what_to_do": "Мониторьте доноров, избегайте ссылок с подозрительных TLD и страниц-линкопомоек.",
                    }
                )

        prio_order = {"high": 0, "medium": 1, "low": 2}
        items = sorted(items, key=lambda x: prio_order.get(str(x.get("priority")), 9))

        if use_ai:
            resolved = await ai_runtime_service.resolve(db)
        else:
            resolved = {}
        if use_ai and resolved.get("effective_provider") == "ollama" and resolved.get("effective_model"):
            context = {
                "site_id": site_id,
                "domain": site.domain,
                "scan": {
                    "status_code": scan.status_code if scan else None,
                    "response_time_ms": scan.response_time_ms if scan else None,
                    "title_length": scan.title_length if scan else None,
                    "h1_present": scan.h1_present if scan else None,
                    "indexed": scan.indexed if scan else None,
                    "health_score": scan.health_score if scan else None,
                }
                if scan
                else None,
                "robots": robots.value_json if robots else None,
                "sitemap": sitemap.value_json if sitemap else None,
                "links_ahrefs": ahrefs.value_json if ahrefs else None,
            }
            improved = await ai_service.enhance_recommendations_ai(
                context=context,
                items=items,
                model=str(resolved["effective_model"]),
            )
            if improved is not None:
                items = improved

        return {"site_id": site_id, "domain": site.domain, "items": items}


recommendations_service = RecommendationsService()
