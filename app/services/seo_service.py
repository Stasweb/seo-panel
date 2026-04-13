import httpx
from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Any
from datetime import datetime
from app.core.config import settings
from app.schemas.schemas import AuditResult
import collections
import re
from urllib.parse import urlparse

class SEOService:
    """
    Service for SEO tools and checks.
    """
    def __init__(self):
        self.headers = {"User-Agent": settings.USER_AGENT}

    async def check_url(self, url: str) -> AuditResult:
        """
        Check URL status, title, H1 and basic indexing check.
        """
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
            try:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, 'lxml')

                title = soup.title.string.strip() if soup.title else None
                h1 = soup.find('h1').get_text(strip=True) if soup.find('h1') else None

                parsed = urlparse(str(response.url))
                domain = parsed.netloc or parsed.path
                is_indexed = await self.check_indexed(domain)

                return AuditResult(
                    url=url,
                    status_code=response.status_code,
                    title=title,
                    title_length=len(title) if title else 0,
                    h1=h1,
                    is_indexed=is_indexed,
                    last_check=datetime.utcnow()
                )
            except Exception as e:
                return AuditResult(
                    url=url,
                    status_code=None,
                    title=None,
                    title_length=0,
                    h1=None,
                    is_indexed=False,
                    last_check=datetime.utcnow()
                )

    async def check_indexed(self, domain: str) -> Optional[bool]:
        """
        Lightweight indexing check via HTML search results (no paid APIs).
        Uses DuckDuckGo HTML endpoint as a best-effort signal.
        """
        domain = domain.strip().lower()
        if not domain:
            return None

        query_url = "https://duckduckgo.com/html/"
        params = {"q": f"site:{domain}"}
        async with httpx.AsyncClient(headers=self.headers, timeout=10.0, follow_redirects=True) as client:
            try:
                resp = await client.get(query_url, params=params)
                if resp.status_code != 200:
                    return None
                soup = BeautifulSoup(resp.text, "lxml")
                results = soup.select(".results .result") or soup.select(".result")
                return len(results) > 0
            except Exception:
                return None

    def calculate_keyword_density(self, text: str) -> List[Dict[str, Any]]:
        """
        Calculate keyword density without heavy NLP libraries.
        """
        # Simple cleanup
        words = re.findall(r'\w+', text.lower())
        stop_words = {'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы'}

        filtered_words = [w for w in words if len(w) > 2 and w not in stop_words]
        total_count = len(filtered_words)

        if total_count == 0:
            return []

        word_counts = collections.Counter(filtered_words)
        density = []
        for word, count in word_counts.most_common(10):
            density.append({
                "keyword": word,
                "count": count,
                "percentage": round((count / total_count) * 100, 2)
            })

        return density

    def generate_meta_description(self, content: str, max_length: int = 160) -> str:
        """
        Simple meta description generator based on content.
        """
        # Cleanup and get first sentences
        content = content.strip()
        if not content:
            return ""

        # Get first ~200 chars and cut at space
        desc = content[:max_length + 20]
        if len(desc) > max_length:
            desc = desc[:max_length].rsplit(' ', 1)[0] + "..."

        return desc

seo_service = SEOService()
