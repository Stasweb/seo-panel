from __future__ import annotations

from typing import Optional


PRESET_USER_AGENTS = {
    "googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "bingbot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "yandexbot": "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
}


def resolve_user_agent(choice: Optional[str], custom: Optional[str], fallback: str) -> str:
    """
    Resolve selected user-agent for all HTTP requests.

    choice:
      - googlebot | bingbot | yandexbot | custom | None
    """
    c = (choice or "").strip().lower()
    if c == "custom":
        return (custom or "").strip() or fallback
    if c in PRESET_USER_AGENTS:
        return PRESET_USER_AGENTS[c]
    return fallback
