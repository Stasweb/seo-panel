from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Task, Site
from app.services.recommendations_service import recommendations_service
from app.utils.time import utcnow


def _priority_to_task_priority(p: str) -> str:
    v = (p or "").strip().lower()
    if v == "high":
        return "high"
    if v == "low":
        return "low"
    return "normal"


def _priority_sla_days(task_priority: str) -> int:
    v = (task_priority or "").strip().lower()
    if v == "high":
        return 3
    if v == "low":
        return 14
    return 7


class AutoTaskService:
    async def sync_site(
        self,
        db: AsyncSession,
        *,
        site_id: int,
        max_tasks: int = 8,
        include_low: bool = False,
    ) -> Dict[str, Any]:
        site = await db.get(Site, int(site_id))
        if not site:
            return {"ok": False, "detail": "Site not found"}

        rec = await recommendations_service.generate(db, site_id=int(site_id), use_ai=False)
        items = list(rec.get("items") or [])
        if not include_low:
            items = [x for x in items if str(x.get("priority") or "").lower() in ("high", "medium")]
        items = items[: max(1, min(30, int(max_tasks)))]

        titles = []
        prepared: List[Dict[str, Any]] = []
        for it in items:
            title_base = str(it.get("title") or "").strip()
            if not title_base:
                continue
            task_title = f"Авто: {title_base}"
            if len(task_title) > 255:
                task_title = task_title[:255]
            tprio = _priority_to_task_priority(str(it.get("priority") or "normal"))
            sla_days = _priority_sla_days(tprio)
            deadline = (utcnow() + timedelta(days=sla_days)).date()
            prepared.append(
                {
                    "title": task_title,
                    "priority": tprio,
                    "deadline": deadline,
                    "what_to_do": str(it.get("what_to_do") or "").strip(),
                }
            )
            titles.append(task_title)

        if not prepared:
            return {"ok": True, "created": 0, "updated": 0, "skipped": 0, "task_ids": []}

        existing = (
            await db.execute(
                select(Task).where(Task.site_id == int(site_id), Task.status != "done", Task.title.in_(titles))
            )
        ).scalars().all()
        by_title = {str(t.title): t for t in existing}

        created = 0
        updated = 0
        skipped = 0
        ids: List[int] = []
        for p in prepared:
            title = p["title"]
            row = by_title.get(title)
            desc_lines = [
                f"Сайт: {site.domain}",
                "Источник: автозадачи (тех. проверки/рекомендации)",
            ]
            if p.get("what_to_do"):
                desc_lines.append("")
                desc_lines.append("Что делать:")
                desc_lines.append(p["what_to_do"])
            desc = "\n".join(desc_lines)

            if row:
                changed = False
                if row.priority != p["priority"]:
                    row.priority = p["priority"]
                    changed = True
                if row.deadline != p["deadline"]:
                    row.deadline = p["deadline"]
                    changed = True
                if (row.description or "").strip() != desc.strip():
                    row.description = desc
                    changed = True
                if changed:
                    db.add(row)
                    updated += 1
                else:
                    skipped += 1
                ids.append(int(row.id))
                continue

            new_task = Task(
                site_id=int(site_id),
                title=title,
                description=desc,
                status="todo",
                priority=p["priority"],
                deadline=p["deadline"],
                source_url=None,
                deep_audit_report_id=None,
            )
            db.add(new_task)
            await db.flush()
            ids.append(int(new_task.id))
            created += 1

        await db.commit()
        return {"ok": True, "created": created, "updated": updated, "skipped": skipped, "task_ids": ids}


auto_task_service = AutoTaskService()

