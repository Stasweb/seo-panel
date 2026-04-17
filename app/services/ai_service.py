from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
import collections
import json

from app.services.ollama_client import ollama_client


RUS_STOP_WORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она",
    "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по", "только", "ее",
    "мне", "было", "вот", "от", "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда",
    "даже", "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был", "него", "до",
    "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей",
    "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем",
    "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет",
    "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним",
    "здесь", "этом", "один", "почти", "мой", "тем", "чтобы",
}


def _normalize_words(text: str) -> List[str]:
    words = re.findall(r"\w+", (text or "").lower())
    return [w for w in words if len(w) > 2 and w not in RUS_STOP_WORDS]


def _top_keywords(text: str, limit: int = 10) -> List[Dict[str, Any]]:
    words = _normalize_words(text)
    if not words:
        return []
    counter = collections.Counter(words)
    total = len(words)
    out: List[Dict[str, Any]] = []
    for word, count in counter.most_common(limit):
        out.append(
            {
                "keyword": word,
                "count": count,
                "percentage": round((count / total) * 100, 2),
            }
        )
    return out


def _highlight_keywords(text: str, keywords: List[str]) -> str:
    if not text or not keywords:
        return text or ""
    escaped = [re.escape(k) for k in keywords if k]
    if not escaped:
        return text
    pattern = re.compile(rf"\b({'|'.join(escaped)})\b", re.IGNORECASE)
    return pattern.sub(r"**\1**", text)


class AIService:
    """
    Lightweight "pseudo-AI" utilities without external paid APIs.
    """

    def generate_meta(self, text: str, max_length: int = 160) -> Dict[str, Any]:
        """
        Generate meta description with keyword highlighting (markdown-style **kw**).
        """
        text = (text or "").strip()
        if not text:
            return {"meta": "", "keywords": []}

        base = re.sub(r"\s+", " ", text)
        snippet = base[: max_length + 40]
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(" ", 1)[0].rstrip() + "..."

        keywords = [k["keyword"] for k in _top_keywords(text, limit=5)]
        highlighted = _highlight_keywords(snippet, keywords)

        return {"meta": highlighted, "keywords": keywords, "length": len(snippet)}

    def keyword_suggestions(self, text: str, limit: int = 10) -> Dict[str, Any]:
        """
        Return top keywords by frequency.
        """
        return {"keywords": _top_keywords(text, limit=limit)}

    def title_check(self, title: str) -> Dict[str, Any]:
        """
        Check title length and give recommendations.
        """
        title = (title or "").strip()
        length = len(title)

        min_len = 30
        max_len = 65

        if length == 0:
            status = "empty"
            recommendation = "Добавь Title: 30–65 символов, с ключевой фразой ближе к началу."
        elif length < min_len:
            status = "too_short"
            recommendation = "Слишком короткий Title. Расширь до 30–65 символов, добавь уточнение/УТП."
        elif length > max_len:
            status = "too_long"
            recommendation = "Слишком длинный Title. Сократи до 30–65 символов, убери повторяющиеся слова."
        else:
            status = "ok"
            recommendation = "Длина Title в норме. Проверь читабельность и наличие ключа."

        return {"status": status, "length": length, "recommendation": recommendation}

    async def generate_meta_ai(self, text: str, *, max_length: int, model: str) -> Optional[Dict[str, Any]]:
        text = (text or "").strip()
        if not text:
            return {"meta": "", "keywords": [], "length": 0}
        system = (
            "Ты SEO-ассистент. Верни строго JSON без markdown.\n"
            "Схема: {\"meta\": string, \"keywords\": [string], \"length\": number}.\n"
            f"meta: на русском, максимум {int(max_length)} символов, без кавычек-ёлочек, без эмодзи.\n"
            "keywords: 5 ключевых фраз/слов из текста.\n"
        )
        user = f"Текст:\n{text}"
        try:
            content = await ollama_client.chat_json(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            data = _safe_json(content)
            if not isinstance(data, dict):
                return None
            meta = str(data.get("meta") or "").strip()
            if not meta:
                return None
            if len(meta) > int(max_length):
                meta = meta[: int(max_length)].rsplit(" ", 1)[0].rstrip()
            kws = data.get("keywords") or []
            if not isinstance(kws, list):
                kws = []
            kws = [str(k).strip() for k in kws if str(k).strip()][:5]
            return {"meta": meta, "keywords": kws, "length": len(meta)}
        except Exception:
            return None

    async def keyword_suggestions_ai(self, text: str, *, limit: int, model: str) -> Optional[Dict[str, Any]]:
        text = (text or "").strip()
        if not text:
            return {"keywords": []}
        system = (
            "Ты SEO-ассистент. Верни строго JSON без markdown.\n"
            "Схема: {\"keywords\": [{\"keyword\": string, \"count\": number, \"percentage\": number}]}.\n"
            f"Верни топ-{int(limit)} ключевых слов/фраз по важности. count и percentage могут быть приблизительными.\n"
        )
        user = f"Текст:\n{text}"
        try:
            content = await ollama_client.chat_json(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.1,
            )
            data = _safe_json(content)
            if not isinstance(data, dict):
                return None
            items = data.get("keywords") or []
            if not isinstance(items, list):
                return None
            out = []
            for it in items[: int(limit)]:
                if not isinstance(it, dict):
                    continue
                kw = str(it.get("keyword") or "").strip()
                if not kw:
                    continue
                out.append(
                    {
                        "keyword": kw,
                        "count": int(float(it.get("count") or 0)),
                        "percentage": float(it.get("percentage") or 0.0),
                    }
                )
            return {"keywords": out}
        except Exception:
            return None

    async def title_check_ai(self, title: str, *, model: str) -> Optional[Dict[str, Any]]:
        title = (title or "").strip()
        system = (
            "Ты SEO-ассистент. Верни строго JSON без markdown.\n"
            "Схема: {\"status\": \"empty\"|\"too_short\"|\"too_long\"|\"ok\", \"length\": number, \"recommendation\": string}.\n"
            "Оценка по длине: 30..65 символов. recommendation на русском.\n"
        )
        user = f"Title:\n{title}"
        try:
            content = await ollama_client.chat_json(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            data = _safe_json(content)
            if not isinstance(data, dict):
                return None
            status = str(data.get("status") or "").strip()
            if status not in {"empty", "too_short", "too_long", "ok"}:
                return None
            rec = str(data.get("recommendation") or "").strip()
            if not rec:
                return None
            return {"status": status, "length": len(title), "recommendation": rec}
        except Exception:
            return None

    async def enhance_recommendations_ai(self, *, context: Dict[str, Any], items: List[Dict[str, Any]], model: str) -> Optional[List[Dict[str, Any]]]:
        system = (
            "Ты SEO-ассистент для панели мониторинга.\n"
            "На входе: JSON с context и items.\n"
            "Нужно: вернуть строго JSON без markdown.\n"
            "Схема: {\"items\": [{\"priority\": \"high\"|\"medium\"|\"low\", \"title\": string, \"what_to_do\": string}]}.\n"
            "Правила:\n"
            "- Сохраняй смысл текущих items, но перепиши более полезно/конкретно.\n"
            "- Можно добавить до 3 новых пунктов, если есть явные пробелы.\n"
            "- Не добавляй выдуманные факты. Если данных нет — не делай вывод.\n"
            "- what_to_do: 1–2 предложения, без эмодзи.\n"
            "- Не упоминай слово 'Ollama' и технические детали.\n"
        )
        user = json.dumps({"context": context, "items": items}, ensure_ascii=False)
        try:
            content = await ollama_client.chat_json(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            data = _safe_json(content)
            if not isinstance(data, dict):
                return None
            out = data.get("items")
            if not isinstance(out, list) or not out:
                return None
            norm: List[Dict[str, Any]] = []
            for it in out[: max(1, min(20, len(items) + 3))]:
                if not isinstance(it, dict):
                    continue
                pr = str(it.get("priority") or "").strip().lower()
                if pr not in {"high", "medium", "low"}:
                    continue
                title = str(it.get("title") or "").strip()
                todo = str(it.get("what_to_do") or "").strip()
                if not title or not todo:
                    continue
                norm.append({"priority": pr, "title": title, "what_to_do": todo})
            if not norm:
                return None
            return norm
        except Exception:
            return None

    async def explain_audit_ai(self, *, audit: Dict[str, Any], model: str) -> Optional[Dict[str, Any]]:
        system = (
            "Ты SEO-ассистент. Объясни результат быстрой SEO-проверки URL.\n"
            "Верни строго JSON без markdown.\n"
            "Схема: {\"summary\": string, \"actions\": [string]}.\n"
            "Правила:\n"
            "- summary: 2–4 предложения на русском, без эмодзи.\n"
            "- actions: 3–7 коротких шагов (по 1 предложению), только то, что следует из входных данных.\n"
            "- Не выдумывай статус индексации: если is_indexed=null — не утверждай 'в индексе/не в индексе'.\n"
        )
        user = json.dumps(audit, ensure_ascii=False)
        try:
            content = await ollama_client.chat_json(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            data = _safe_json(content)
            if not isinstance(data, dict):
                return None
            summary = str(data.get("summary") or "").strip()
            actions = data.get("actions") or []
            if not summary or not isinstance(actions, list):
                return None
            actions = [str(a).strip() for a in actions if str(a).strip()][:7]
            if not actions:
                return None
            return {"summary": summary, "actions": actions}
        except Exception:
            return None

    async def explain_deep_audit_ai(self, *, audit: Dict[str, Any], model: str) -> Optional[Dict[str, Any]]:
        system = (
            "Ты SEO-ассистент. На входе JSON с результатом углублённой SEO-проверки URL.\n"
            "Верни строго JSON без markdown.\n"
            "Схема: {\"summary\": string, \"actions\": [string]}.\n"
            "Правила:\n"
            "- summary: 3–6 предложений на русском, без эмодзи.\n"
            "- actions: 5–10 шагов (по 1 предложению), только из входных данных.\n"
            "- Если indexable=false — первые шаги про причины (robots/canonical/http).\n"
            "- Если keyword_suggestions присутствуют — используй их как подсказки (без гарантии позиций).\n"
            "- Если spam_flags/spam_score присутствуют — добавь действия по снижению спама (переписать title/h1, уменьшить повторы, убрать агрессивные элементы).\n"
            "- Если target_keyword_stats присутствует — учитывай плотность и повторы целевого ключа.\n"
        )
        user = json.dumps(audit, ensure_ascii=False)
        try:
            content = await ollama_client.chat_json(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            data = _safe_json(content)
            if not isinstance(data, dict):
                return None
            summary = str(data.get("summary") or "").strip()
            actions = data.get("actions") or []
            if not summary or not isinstance(actions, list):
                return None
            actions = [str(a).strip() for a in actions if str(a).strip()][:10]
            if not actions:
                return None
            return {"summary": summary, "actions": actions}
        except Exception:
            return None

    async def enhance_competitor_issues_ai(self, *, context: Dict[str, Any], issues: List[Dict[str, Any]], model: str) -> Optional[List[Dict[str, Any]]]:
        system = (
            "Ты SEO-ассистент. На входе JSON с данными конкурента и issues.\n"
            "Верни строго JSON без markdown.\n"
            "Схема: {\"issues\": [{\"priority\": \"high\"|\"medium\"|\"low\", \"title\": string, \"what_to_do\": string}]}.\n"
            "Правила:\n"
            "- Используй только переданные факты.\n"
            "- Перепиши и дополни issues (до 10) с конкретными действиями.\n"
            "- what_to_do: 1–2 предложения, без эмодзи.\n"
        )
        user = json.dumps({"context": context, "issues": issues}, ensure_ascii=False)
        try:
            content = await ollama_client.chat_json(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            data = _safe_json(content)
            if not isinstance(data, dict):
                return None
            out = data.get("issues")
            if not isinstance(out, list) or not out:
                return None
            norm: List[Dict[str, Any]] = []
            for it in out[:10]:
                if not isinstance(it, dict):
                    continue
                pr = str(it.get("priority") or "").strip().lower()
                if pr not in {"high", "medium", "low"}:
                    continue
                title = str(it.get("title") or "").strip()
                todo = str(it.get("what_to_do") or "").strip()
                if not title or not todo:
                    continue
                norm.append({"priority": pr, "title": title, "what_to_do": todo})
            if not norm:
                return None
            return norm
        except Exception:
            return None


def _safe_json(text: str) -> Any:
    s = (text or "").strip()
    if not s:
        return None
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", s)
        s = s.strip()
        if s.endswith("```"):
            s = s[: -3].strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


ai_service = AIService()
