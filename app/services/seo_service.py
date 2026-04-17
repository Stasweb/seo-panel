from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Any
from datetime import datetime
from app.core.config import settings
from app.schemas.schemas import AuditResult
import collections
import re
from urllib.parse import urlparse
from app.core.http_client import http_service
from app.utils.time import utcnow
from app.utils.user_agents import resolve_user_agent
from app.services.keyword_suggest_service import keyword_suggest_service
import httpx
import time

class SEOService:
    """
    Service for SEO tools and checks.
    """
    def __init__(self):
        self.headers = {"User-Agent": settings.USER_AGENT}

    async def check_url(
        self,
        url: str,
        *,
        user_agent: Optional[str] = None,
        user_agent_choice: Optional[str] = None,
        custom_user_agent: Optional[str] = None,
    ) -> AuditResult:
        """
        Check URL status, title, H1 and basic indexing check.
        """
        if settings.TESTING:
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            return AuditResult(
                url=url,
                status_code=200,
                title="TEST",
                title_length=4,
                h1="TEST",
                is_indexed=True,
                last_check=utcnow(),
            )
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        ua = user_agent or resolve_user_agent(user_agent_choice, custom_user_agent, settings.USER_AGENT)
        try:
            res = await http_service.get_text(
                url,
                user_agent=ua,
                cache_key=f"audit:{url}:{ua}",
                timeout=10.0,
                follow_redirects=True,
            )
            soup = BeautifulSoup(res.text, "lxml")

            title = soup.title.string.strip() if soup.title else None
            h1 = soup.find("h1").get_text(strip=True) if soup.find("h1") else None

            parsed = urlparse(str(res.url))
            domain = parsed.netloc or parsed.path
            try:
                is_indexed = await self.check_indexed(domain, probe=user_agent_choice, user_agent=ua)
            except Exception:
                is_indexed = None

            if is_indexed is None and 200 <= int(res.status_code) < 400:
                xrt = (res.headers.get("x-robots-tag") or "").lower()
                meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
                meta_content = ((meta.get("content") if meta else "") or "").lower()
                noindex = ("noindex" in xrt) or ("noindex" in meta_content)
                is_indexed = False if noindex else True

            return AuditResult(
                url=url,
                status_code=res.status_code,
                title=title,
                title_length=len(title) if title else 0,
                h1=h1,
                is_indexed=is_indexed,
                last_check=utcnow(),
            )
        except Exception:
            return AuditResult(
                url=url,
                status_code=None,
                title=None,
                title_length=0,
                h1=None,
                is_indexed=None,
                last_check=utcnow(),
            )

    async def deep_audit_url(
        self,
        url: str,
        *,
        user_agent_choice: Optional[str] = None,
        custom_user_agent: Optional[str] = None,
        suggest_mode: str = "expanded",
        suggest_variants: int = 15,
        target_keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        if settings.TESTING:
            return {
                "url": url,
                "final_url": url,
                "status_code": 200,
                "response_time_ms": 10,
                "title": "TEST",
                "title_length": 4,
                "meta_description": "TEST",
                "meta_description_length": 4,
                "canonical": url,
                "robots_meta": "index,follow",
                "x_robots_tag": None,
                "h1": "TEST",
                "headings": {"h1": 1, "h2": 2, "h3": 0},
                "word_count": 100,
                "links_internal": 5,
                "links_external": 2,
                "images_total": 3,
                "images_missing_alt": 1,
                "og_tags": True,
                "viewport": True,
                "structured_data_count": 1,
                "hreflang_count": 0,
                "is_indexed": True,
                "indexable": True,
                "indexability_reasons": [],
                "keyword_suggestions": {"title": {"items": {"google": ["test"]}}, "h1": {"items": {"google": ["test"]}}},
                "last_check": utcnow().isoformat(),
            }

        ua = resolve_user_agent(user_agent_choice, custom_user_agent, settings.USER_AGENT)
        try:
            started = time.monotonic()
            async with httpx.AsyncClient(headers={"User-Agent": ua}, timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(url)
            elapsed_ms = int(round((time.monotonic() - started) * 1000.0))
            final_url = str(resp.url)
            status_code = int(resp.status_code)
            html = resp.text or ""
            x_robots_tag = (resp.headers.get("x-robots-tag") or "").strip() or None
        except Exception as e:
            return {
                "url": url,
                "final_url": None,
                "status_code": None,
                "response_time_ms": None,
                "title": None,
                "title_length": 0,
                "meta_description": None,
                "meta_description_length": 0,
                "canonical": None,
                "robots_meta": None,
                "x_robots_tag": None,
                "h1": None,
                "headings": None,
                "word_count": None,
                "links_internal": None,
                "links_external": None,
                "images_total": None,
                "images_missing_alt": None,
                "og_tags": None,
                "viewport": None,
                "structured_data_count": None,
                "hreflang_count": None,
                "is_indexed": None,
                "indexable": None,
                "indexability_reasons": [str(e)],
                "keyword_suggestions": {},
                "last_check": utcnow().isoformat(),
            }

        soup = BeautifulSoup(html, "lxml")
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        meta_desc = None
        md_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if md_tag:
            meta_desc = (md_tag.get("content") or "").strip() or None
        canon = None
        canon_tag = soup.find("link", attrs={"rel": re.compile(r"^canonical$", re.I)})
        if canon_tag:
            canon = (canon_tag.get("href") or "").strip() or None
        robots_meta = None
        robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if robots_tag:
            robots_meta = (robots_tag.get("content") or "").strip() or None

        h1_tag = soup.find("h1")
        h1 = (h1_tag.get_text(strip=True) if h1_tag else None) or None

        headings = {
            "h1": len(soup.find_all("h1")),
            "h2": len(soup.find_all("h2")),
            "h3": len(soup.find_all("h3")),
        }

        text = soup.get_text(" ", strip=True)
        word_count = len([w for w in re.split(r"\s+", text) if w])

        parsed = urlparse(final_url)
        host = (parsed.netloc or "").lower()
        links_internal = 0
        links_external = 0
        for a in soup.find_all("a"):
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            if href.startswith("/"):
                links_internal += 1
                continue
            if href.startswith(("http://", "https://")):
                try:
                    h = urlparse(href).netloc.lower()
                except Exception:
                    h = ""
                if h and host and h.endswith(host):
                    links_internal += 1
                else:
                    links_external += 1
                continue
            links_internal += 1

        imgs = soup.find_all("img")
        images_total = len(imgs)
        images_missing_alt = 0
        for img in imgs:
            alt = (img.get("alt") or "").strip()
            if not alt:
                images_missing_alt += 1

        og_tags = soup.find("meta", attrs={"property": re.compile(r"^og:", re.I)}) is not None
        viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)}) is not None
        structured_data_count = len(soup.find_all("script", attrs={"type": re.compile(r"application/ld\\+json", re.I)}))
        hreflang_count = len(soup.find_all("link", attrs={"rel": re.compile(r"alternate", re.I), "hreflang": True}))

        spam = self._spam_signals(title=title, h1=h1, meta_description=meta_desc, text=text)
        kw_stats = self._target_keyword_stats(target_keyword, title=title, h1=h1, meta_description=meta_desc, text=text)
        if kw_stats.get("is_spam"):
            spam["flags"] = list(spam.get("flags") or []) + list(kw_stats.get("spam_flags") or [])
            spam["score"] = max(int(spam.get("score") or 0), int(kw_stats.get("spam_score") or 0))

        noindex = False
        reasons: List[str] = []
        if not (200 <= status_code < 300):
            reasons.append(f"HTTP {status_code}")
        robots_combo = f"{robots_meta or ''} {x_robots_tag or ''}".lower()
        if "noindex" in robots_combo:
            noindex = True
            reasons.append("noindex (robots meta / x-robots-tag)")
        if canon and host:
            try:
                canon_host = urlparse(canon).netloc.lower()
            except Exception:
                canon_host = ""
            if canon_host and canon_host != host:
                reasons.append("canonical ведёт на другой домен")

        indexable = (200 <= status_code < 300) and (not noindex)
        parsed_domain = urlparse(final_url).netloc or final_url
        try:
            is_indexed = await self.check_indexed(parsed_domain, probe=user_agent_choice)
        except Exception:
            is_indexed = None
        if is_indexed is None and indexable:
            is_indexed = True

        keyword_suggestions: Dict[str, Any] = {}
        title_q = self._normalize_query_for_suggest(title)
        h1_q = self._normalize_query_for_suggest(h1)
        mode = (suggest_mode or "expanded").strip().lower()
        variants = max(1, min(30, int(suggest_variants)))
        if title_q:
            keyword_suggestions["title"] = await keyword_suggest_service.suggest(
                title_q,
                engines=["google", "yandex", "bing", "ddg"],
                lang="ru",
                mode=mode,
                max_variants=variants,
                max_per_engine=30,
            )
        if h1_q and h1_q != title_q:
            keyword_suggestions["h1"] = await keyword_suggest_service.suggest(
                h1_q,
                engines=["google", "yandex", "bing", "ddg"],
                lang="ru",
                mode="basic" if mode == "expanded" else mode,
                max_variants=max(1, min(10, variants)),
                max_per_engine=20,
            )

        return {
            "url": url,
            "final_url": final_url,
            "status_code": status_code,
            "response_time_ms": elapsed_ms,
            "title": title,
            "title_length": len(title) if title else 0,
            "meta_description": meta_desc,
            "meta_description_length": len(meta_desc) if meta_desc else 0,
            "canonical": canon,
            "robots_meta": robots_meta,
            "x_robots_tag": x_robots_tag,
            "h1": h1,
            "headings": headings,
            "word_count": word_count,
            "links_internal": links_internal,
            "links_external": links_external,
            "images_total": images_total,
            "images_missing_alt": images_missing_alt,
            "og_tags": bool(og_tags),
            "viewport": bool(viewport),
            "structured_data_count": structured_data_count,
            "hreflang_count": hreflang_count,
            "is_indexed": is_indexed,
            "indexable": bool(indexable),
            "indexability_reasons": reasons,
            "keyword_suggestions": keyword_suggestions,
            "spam_score": int(spam.get("score") or 0),
            "spam_flags": list(spam.get("flags") or []),
            "title_spam": bool(spam.get("title_spam")),
            "h1_spam": bool(spam.get("h1_spam")),
            "keyword_stuffing": bool(spam.get("keyword_stuffing")),
            "target_keyword": (target_keyword or "").strip() or None,
            "target_keyword_stats": kw_stats if (target_keyword or "").strip() else None,
            "last_check": utcnow().isoformat(),
        }

    def _normalize_query_for_suggest(self, value: Optional[str]) -> Optional[str]:
        s = (value or "").strip()
        if not s:
            return None
        s = re.sub(r"\s+", " ", s)
        if len(s) > 80:
            s = s[:80].rsplit(" ", 1)[0].strip() or s[:80]
        return s or None

    def _spam_signals(
        self,
        *,
        title: Optional[str],
        h1: Optional[str],
        meta_description: Optional[str],
        text: str,
    ) -> Dict[str, Any]:
        flags: List[str] = []
        score = 0

        def _tokenize(s: str) -> List[str]:
            s = (s or "").lower()
            s = re.sub(r"[^\w\s\u0400-\u04ff]", " ", s, flags=re.UNICODE)
            s = re.sub(r"\s+", " ", s).strip()
            parts = [p for p in s.split(" ") if p]
            parts = [p for p in parts if len(p) >= 3 and not p.isdigit()]
            return parts

        def _word_stats(tokens: List[str]) -> Dict[str, Any]:
            total = len(tokens)
            if total == 0:
                return {"total": 0, "top": []}
            c = collections.Counter(tokens)
            top = c.most_common(10)
            return {"total": total, "top": top, "counter": c}

        def _ngram_max(tokens: List[str], n: int) -> int:
            if len(tokens) < n:
                return 0
            grams = [" ".join(tokens[i : i + n]) for i in range(0, len(tokens) - n + 1)]
            return collections.Counter(grams).most_common(1)[0][1] if grams else 0

        def _caps_ratio(s: str) -> float:
            letters = [ch for ch in (s or "") if ch.isalpha()]
            if not letters:
                return 0.0
            up = sum(1 for ch in letters if ch.isupper())
            return up / max(1, len(letters))

        def _title_like_signals(s: Optional[str], *, label: str) -> None:
            nonlocal score
            v = (s or "").strip()
            if not v:
                return
            if len(v) >= 90:
                flags.append(f"{label}: слишком длинный")
                score += 25
            elif len(v) >= 70:
                flags.append(f"{label}: длинный")
                score += 10

            if _caps_ratio(v) >= 0.6:
                flags.append(f"{label}: много CAPS")
                score += 15

            if v.count("!") >= 2 or v.count("?") >= 2:
                flags.append(f"{label}: агрессивная пунктуация")
                score += 10

            if v.count("|") + v.count("—") + v.count("-") >= 4:
                flags.append(f"{label}: много разделителей")
                score += 8

            tokens = _tokenize(v)
            st = _word_stats(tokens)
            if st["total"]:
                top_word, top_cnt = st["top"][0]
                if top_cnt >= 3:
                    flags.append(f"{label}: повтор слова '{top_word}'")
                    score += 12

        def _meta_signals(s: Optional[str]) -> None:
            nonlocal score
            v = (s or "").strip()
            if not v:
                return
            if len(v) >= 220:
                flags.append("meta: слишком длинное")
                score += 12
            tokens = _tokenize(v)
            st = _word_stats(tokens)
            if st["total"]:
                top_word, top_cnt = st["top"][0]
                if top_cnt >= 4:
                    flags.append(f"meta: повтор слова '{top_word}'")
                    score += 10

        def _body_keyword_stuffing(body_text: str) -> None:
            nonlocal score
            tokens = _tokenize(body_text)
            st = _word_stats(tokens)
            total = int(st.get("total") or 0)
            if total < 120:
                return
            top = st.get("top") or []
            if top:
                top_word, top_cnt = top[0]
                top_pct = top_cnt / max(1, total)
                if top_pct >= 0.12:
                    flags.append(f"текст: высокий повтор '{top_word}' ({round(top_pct*100, 1)}%)")
                    score += 25
                elif top_pct >= 0.08:
                    flags.append(f"текст: повтор '{top_word}' ({round(top_pct*100, 1)}%)")
                    score += 12
                top3 = sum(int(c) for _, c in top[:3])
                top3_pct = top3 / max(1, total)
                if top3_pct >= 0.22:
                    flags.append("текст: высокая концентрация топ-слов")
                    score += 12

            bigram_max = _ngram_max(tokens, 2)
            trigram_max = _ngram_max(tokens, 3)
            if trigram_max >= 5 or bigram_max >= 8:
                flags.append("текст: возможный keyword stuffing (повтор фраз)")
                score += 18

        _title_like_signals(title, label="title")
        _title_like_signals(h1, label="h1")
        _meta_signals(meta_description)
        _body_keyword_stuffing(text)

        title_tokens = _tokenize(title or "")
        h1_tokens = _tokenize(h1 or "")
        title_spam = any(x.startswith("title:") for x in flags)
        h1_spam = any(x.startswith("h1:") for x in flags)
        keyword_stuffing = any(x.startswith("текст:") for x in flags)

        if title_tokens and h1_tokens and " ".join(title_tokens[:8]) == " ".join(h1_tokens[:8]):
            flags.append("title/h1: слишком похожи")
            score += 6

        score = max(0, min(100, int(score)))
        return {"score": score, "flags": flags[:20], "title_spam": title_spam, "h1_spam": h1_spam, "keyword_stuffing": keyword_stuffing}

    def _target_keyword_stats(
        self,
        target_keyword: Optional[str],
        *,
        title: Optional[str],
        h1: Optional[str],
        meta_description: Optional[str],
        text: str,
    ) -> Dict[str, Any]:
        kw = (target_keyword or "").strip().lower()
        if not kw or len(kw) < 3:
            return {}

        def _normalize(s: str) -> str:
            s = (s or "").lower()
            s = re.sub(r"\s+", " ", s).strip()
            return s

        def _tokenize(s: str) -> List[str]:
            s = (s or "").lower()
            s = re.sub(r"[^\w\s\u0400-\u04ff]", " ", s, flags=re.UNICODE)
            s = re.sub(r"\s+", " ", s).strip()
            return [p for p in s.split(" ") if p]

        def _count_occurrences(hay: str, needle: str) -> int:
            if not hay or not needle:
                return 0
            return len(re.findall(re.escape(needle), hay, flags=re.I))

        kw_norm = _normalize(kw)
        title_norm = _normalize(title or "")
        h1_norm = _normalize(h1 or "")
        meta_norm = _normalize(meta_description or "")
        body_norm = _normalize(text or "")

        title_count = _count_occurrences(title_norm, kw_norm)
        h1_count = _count_occurrences(h1_norm, kw_norm)
        meta_count = _count_occurrences(meta_norm, kw_norm)
        body_count = _count_occurrences(body_norm, kw_norm)

        tokens = _tokenize(text or "")
        total_words = len([t for t in tokens if t and not t.isdigit()])
        kw_words = [w for w in _tokenize(kw_norm) if w and not w.isdigit()]
        kw_len = len(kw_words)

        phrase_repeats = 0
        if kw_len >= 2 and tokens:
            grams = [" ".join(tokens[i : i + kw_len]) for i in range(0, len(tokens) - kw_len + 1)]
            phrase_repeats = sum(1 for g in grams if g == kw_norm)

        density_pct = 0.0
        if total_words and kw_len:
            density_pct = round((phrase_repeats * kw_len / total_words) * 100.0, 2)

        spam_flags: List[str] = []
        spam_score = 0
        if title_count >= 2:
            spam_flags.append("target_kw: повтор в title")
            spam_score += 18
        if h1_count >= 2:
            spam_flags.append("target_kw: повтор в h1")
            spam_score += 18
        if meta_count >= 3:
            spam_flags.append("target_kw: повтор в meta")
            spam_score += 12
        if total_words >= 120:
            if density_pct >= 4.5:
                spam_flags.append(f"target_kw: высокая плотность ({density_pct}%)")
                spam_score += 30
            elif density_pct >= 3.0:
                spam_flags.append(f"target_kw: повышенная плотность ({density_pct}%)")
                spam_score += 16
            if phrase_repeats >= 10:
                spam_flags.append("target_kw: частый повтор фразы")
                spam_score += 18

        spam_score = max(0, min(100, int(spam_score)))
        return {
            "keyword": kw_norm,
            "title_count": int(title_count),
            "h1_count": int(h1_count),
            "meta_count": int(meta_count),
            "body_count": int(body_count),
            "phrase_repeats": int(phrase_repeats),
            "total_words": int(total_words),
            "density_pct": float(density_pct),
            "spam_score": int(spam_score),
            "spam_flags": spam_flags,
            "is_spam": bool(spam_flags),
        }

    async def check_indexed(
        self,
        domain: str,
        *,
        user_agent: Optional[str] = None,
        probe: Optional[str] = None,
    ) -> Optional[bool]:
        """
        Lightweight indexing check via HTML search results (no paid APIs).
        Best-effort: for yandexbot -> Yandex first; for bingbot -> Bing first; otherwise DuckDuckGo (html + lite) and Bing.
        """
        normalized = self._normalize_domain_for_site_query(domain)
        if not normalized:
            return None
        if settings.TESTING:
            return True

        search_ua = settings.USER_AGENT
        probe_key = (probe or "").strip().lower() or None
        q = f"site:{normalized}"

        def _looks_blocked(text: str) -> bool:
            t = (text or "").lower()
            patterns = [
                r"captcha",
                r"verify you are (a )?human",
                r"unusual traffic",
                r"automated queries",
                r"temporarily blocked",
                r"access denied",
                r"enable javascript",
                r"подтвердите,? что вы не робот",
                r"проверка безопасности",
                r"введите символы",
                r"капча",
            ]
            return any(re.search(p, t) for p in patterns)

        async def _try_yandex() -> Optional[bool]:
            url = f"https://yandex.ru/search/?text={q}"
            res = await http_service.get_text(
                url,
                user_agent=search_ua,
                cache_key=f"indexed:yandex:{q}",
                timeout=10.0,
                follow_redirects=True,
            )
            if not (200 <= res.status_code < 400):
                return None
            if _looks_blocked(res.text or ""):
                return None
            soup = BeautifulSoup(res.text, "lxml")
            if soup.select(".serp-item") or soup.select("li.serp-item"):
                return True
            if soup.find(string=re.compile(r"ничего не нашли|не нашлось|результатов: 0|по вашему запросу ничего не найдено", re.I)):
                return False
            return None

        async def _try_ddg_html() -> Optional[bool]:
            url = f"https://duckduckgo.com/html/?q={q}"
            res = await http_service.get_text(
                url,
                user_agent=search_ua,
                cache_key=f"indexed:ddg_html:{q}",
                timeout=10.0,
                follow_redirects=True,
            )
            if not (200 <= res.status_code < 400):
                return None
            if _looks_blocked(res.text or ""):
                return None
            soup = BeautifulSoup(res.text, "lxml")
            if soup.select_one("input[name='q']") is None and soup.select_one("#logo_homepage_link") is None:
                return None
            results = soup.select(".results .result") or soup.select(".result") or soup.select("a.result__a")
            if results:
                return True
            if soup.select_one(".no-results") or soup.find(string=re.compile(r"No results|0 results", re.I)):
                return False
            return None

        async def _try_ddg_lite() -> Optional[bool]:
            url = f"https://lite.duckduckgo.com/lite/?q={q}"
            res = await http_service.get_text(
                url,
                user_agent=search_ua,
                cache_key=f"indexed:ddg_lite:{q}",
                timeout=10.0,
                follow_redirects=True,
            )
            if not (200 <= res.status_code < 400):
                return None
            if _looks_blocked(res.text or ""):
                return None
            soup = BeautifulSoup(res.text, "lxml")
            links = soup.select("a.result-link") or soup.select("a.result__a") or soup.select("a[href^='http']")
            links = [a for a in links if a.get("href")]
            if len(links) >= 3:
                return True
            if soup.find(string=re.compile(r"No results|0 results", re.I)):
                return False
            return None

        async def _try_bing() -> Optional[bool]:
            url = f"https://www.bing.com/search?q={q}"
            res = await http_service.get_text(
                url,
                user_agent=search_ua,
                cache_key=f"indexed:bing:{q}",
                timeout=10.0,
                follow_redirects=True,
            )
            if not (200 <= res.status_code < 400):
                return None
            if _looks_blocked(res.text or ""):
                return None
            soup = BeautifulSoup(res.text, "lxml")
            if soup.select("li.b_algo"):
                return True
            if soup.find(string=re.compile(r"No results found|There are no results", re.I)):
                return False
            return None

        if probe_key == "yandexbot":
            order = (_try_yandex, _try_bing, _try_ddg_lite, _try_ddg_html)
        elif probe_key == "bingbot":
            order = (_try_bing, _try_ddg_lite, _try_ddg_html)
        else:
            order = (_try_ddg_lite, _try_ddg_html, _try_bing)

        for fn in order:
            try:
                r = await fn()
                if r is not None:
                    return r
            except Exception:
                continue
        return None

    def _normalize_domain_for_site_query(self, value: str) -> Optional[str]:
        v = (value or "").strip()
        if not v:
            return None
        parsed = urlparse(v if "://" in v else f"http://{v}")
        host = (parsed.netloc or parsed.path or "").strip()
        if "/" in host:
            host = host.split("/", 1)[0].strip()
        if ":" in host:
            host = host.split(":", 1)[0].strip()
        host = host.strip().lower().rstrip(".")
        if host.startswith("www."):
            host = host[4:]
        return host or None

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
