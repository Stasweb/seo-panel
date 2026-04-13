from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any
import re
import collections


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


ai_service = AIService()
