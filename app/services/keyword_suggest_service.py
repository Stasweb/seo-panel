from __future__ import annotations

import json
import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from app.core.config import settings
from app.core.http_client import http_service


class KeywordSuggestService:
    async def suggest(
        self,
        query: str,
        *,
        engines: Optional[List[str]] = None,
        lang: str = "ru",
        mode: str = "basic",
        max_variants: int = 30,
        max_per_engine: int = 30,
    ) -> Dict[str, Any]:
        q = (query or "").strip()
        if not q:
            return {"query": "", "items": {}}
        if settings.TESTING:
            return {
                "query": q,
                "mode": mode,
                "items": {"google": [q + " тест"], "yandex": [q + " тест"], "bing": [q + " test"], "ddg": [q + " test"]},
                "meta": {"variants_used": 1, "max_variants": max_variants, "max_per_engine": max_per_engine},
            }

        wanted = [e.strip().lower() for e in (engines or ["google", "yandex", "bing", "ddg"]) if e and e.strip()]
        out: Dict[str, List[str]] = {}
        m = (mode or "basic").strip().lower()
        if m not in {"basic", "expanded"}:
            m = "basic"

        variants = [q] if m == "basic" else self._variants(q, lang=lang, max_variants=max_variants)
        per_engine_variants = {k: variants for k in wanted}
        if m == "expanded":
            for e in wanted:
                if e in {"ddg", "duckduckgo", "bing"}:
                    per_engine_variants[e] = variants[: max(8, min(len(variants), 12))]

        async def run_engine(engine: str) -> None:
            v = per_engine_variants.get(engine) or [q]
            results: List[str] = []
            if engine == "google":
                coros = [self._google(x, lang=lang) for x in v]
            elif engine == "yandex":
                coros = [self._yandex(x, lang=lang) for x in v]
            elif engine == "bing":
                coros = [self._bing(x, lang=lang) for x in v]
            elif engine in {"ddg", "duckduckgo"}:
                coros = [self._ddg(x) for x in v]
                engine = "ddg"
            else:
                return

            for chunk in _chunks(coros, 10):
                try:
                    partial = await asyncio.gather(*chunk, return_exceptions=True)
                except Exception:
                    partial = []
                for p in partial:
                    if isinstance(p, list):
                        results.extend(p)
            out[engine] = self._dedupe(results)[: max(1, min(50, int(max_per_engine)))]

        await asyncio.gather(*[run_engine(e) for e in wanted])
        return {
            "query": q,
            "mode": m,
            "items": out,
            "meta": {"variants_used": len(variants), "max_variants": int(max_variants), "max_per_engine": int(max_per_engine)},
        }

    def _variants(self, q: str, *, lang: str, max_variants: int) -> List[str]:
        base = q.strip()
        if not base:
            return []
        max_variants = max(1, min(80, int(max_variants)))
        variants: List[str] = [base]
        alpha_ru = [chr(c) for c in range(ord("а"), ord("я") + 1)]
        alpha_en = [chr(c) for c in range(ord("a"), ord("z") + 1)]
        digits = [str(i) for i in range(0, 10)]
        common_ru = [
            "купить",
            "цена",
            "стоимость",
            "заказать",
            "доставка",
            "отзывы",
            "сравнение",
            "рейтинг",
            "как",
            "что такое",
            "инструкция",
            "лучший",
            "топ",
            "рядом",
            "видео",
        ]
        common_en = ["buy", "price", "reviews", "best", "top", "near me", "how to", "what is"]

        use_ru = (lang or "").lower().startswith(("ru", "uk", "be", "kk"))
        alpha = alpha_ru if use_ru else alpha_en
        common = common_ru if use_ru else common_en

        for a in alpha:
            if len(variants) >= max_variants:
                break
            variants.append(f"{base} {a}")
        for d in digits:
            if len(variants) >= max_variants:
                break
            variants.append(f"{base} {d}")
        for m in common:
            if len(variants) >= max_variants:
                break
            variants.append(f"{base} {m}")
        return variants[:max_variants]

    def _dedupe(self, items: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for it in items:
            s = str(it or "").strip()
            if not s:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        return out

    async def _google(self, q: str, *, lang: str) -> List[str]:
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&hl={quote_plus(lang)}&q={quote_plus(q)}"
        res = await http_service.get_text(url, user_agent=settings.USER_AGENT, cache_key=f"kw_suggest:google:{lang}:{q}", timeout=10.0, follow_redirects=True)
        if not (200 <= res.status_code < 400):
            return []
        try:
            data = json.loads(res.text)
            items = data[1] if isinstance(data, list) and len(data) > 1 else []
            if not isinstance(items, list):
                return []
            return [str(x).strip() for x in items if str(x).strip()][:20]
        except Exception:
            return []

    async def _bing(self, q: str, *, lang: str) -> List[str]:
        url = f"https://api.bing.com/osjson.aspx?query={quote_plus(q)}&mkt={quote_plus(lang)}"
        res = await http_service.get_text(url, user_agent=settings.USER_AGENT, cache_key=f"kw_suggest:bing:{lang}:{q}", timeout=10.0, follow_redirects=True)
        if not (200 <= res.status_code < 400):
            return []
        try:
            data = json.loads(res.text)
            items = data[1] if isinstance(data, list) and len(data) > 1 else []
            if not isinstance(items, list):
                return []
            return [str(x).strip() for x in items if str(x).strip()][:20]
        except Exception:
            return []

    async def _ddg(self, q: str) -> List[str]:
        url = f"https://duckduckgo.com/ac/?q={quote_plus(q)}&type=list"
        res = await http_service.get_text(url, user_agent=settings.USER_AGENT, cache_key=f"kw_suggest:ddg:{q}", timeout=10.0, follow_redirects=True)
        if not (200 <= res.status_code < 400):
            return []
        try:
            data = json.loads(res.text)
            if not isinstance(data, list):
                return []
            out = []
            for it in data:
                if isinstance(it, dict):
                    phrase = str(it.get("phrase") or "").strip()
                    if phrase:
                        out.append(phrase)
            return out[:20]
        except Exception:
            return []

    async def _yandex(self, q: str, *, lang: str) -> List[str]:
        url = f"https://suggest.yandex.ru/suggest-ya.cgi?v=4&part={quote_plus(q)}&uil={quote_plus(lang)}"
        res = await http_service.get_text(url, user_agent=settings.USER_AGENT, cache_key=f"kw_suggest:yandex:{lang}:{q}", timeout=10.0, follow_redirects=True)
        if not (200 <= res.status_code < 400):
            return []
        try:
            data = json.loads(res.text)
            if isinstance(data, dict):
                items = data.get("text") or data.get("suggest") or data.get("s") or []
                if isinstance(items, list):
                    return [str(x).strip() for x in items if str(x).strip()][:20]
            if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
                return [str(x).strip() for x in data[1] if str(x).strip()][:20]
            return []
        except Exception:
            return []


keyword_suggest_service = KeywordSuggestService()


def _chunks(items: List[Any], size: int) -> List[List[Any]]:
    size = max(1, int(size))
    return [items[i : i + size] for i in range(0, len(items), size)]
