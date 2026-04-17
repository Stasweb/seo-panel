from __future__ import annotations

from typing import Any, Dict, List

import httpx

from app.core.config import settings


class AhrefsService:
    async def refdomains(
        self,
        *,
        api_key: str,
        target: str,
        limit: int = 50,
        history: str = "live",
    ) -> Dict[str, Any]:
        limit = max(1, min(200, int(limit)))
        if settings.TESTING:
            return {
                "ok": True,
                "items": [
                    {
                        "domain": "donor.example",
                        "links_to_target": 10,
                        "domain_rating": 55,
                        "traffic_domain": 123,
                        "dofollow_links": 8,
                        "dofollow_refdomains": 3,
                        "is_spam": False,
                        "first_seen": "2026-04-10",
                        "last_seen": "2026-04-16",
                    }
                ],
            }

        url = "https://api.ahrefs.com/v3/site-explorer/refdomains"
        params = {
            "history": history,
            "limit": str(limit),
            "order_by": "domain_rating:desc,traffic_domain:desc",
            "select": "domain,links_to_target,is_spam,first_seen,last_seen,domain_rating,dofollow_refdomains,dofollow_linked_domains,traffic_domain,positions_source_domain,new_links,lost_links,dofollow_links",
            "target": target,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers, params=params)
        except Exception:
            return {"ok": False, "detail": "Ahrefs request failed"}

        if resp.status_code != 200:
            body = (resp.text or "").strip()
            if len(body) > 400:
                body = body[:400] + "…"
            return {
                "ok": False,
                "http_status": int(resp.status_code),
                "detail": "Ahrefs HTTP error",
                "body_preview": body,
            }

        try:
            data = resp.json()
        except Exception:
            return {"ok": False, "detail": "Ahrefs invalid JSON"}

        items: List[Dict[str, Any]] = []
        raw_items = data.get("refdomains") or data.get("items") or data.get("data") or []
        if isinstance(raw_items, list):
            for it in raw_items:
                if not isinstance(it, dict):
                    continue
                dom = (it.get("domain") or "").strip()
                if not dom:
                    continue
                items.append(it)
        return {"ok": True, "items": items}


ahrefs_service = AhrefsService()
