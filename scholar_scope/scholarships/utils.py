from __future__ import annotations
import random
import string
import hashlib
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache 
import numpy as np
from django.db.models import Count, Q
from django.utils.timezone import now
from pgvector.django import CosineDistance
from typing import Optional, List
import re
import logging
import dateparser
import trafilatura
from parsel import Selector
from difflib import get_close_matches
from datetime import date
import google.generativeai as genai
from openai import AsyncOpenAI
import os
import json
logger = logging.getLogger(__name__)

TOP_K_CHUNKS = 3
import dateparser
import trafilatura
from parsel import Selector  
EMBEDDING_CACHE_TTL = 7 * 24 * 3600  
RECOMMENDATION_CACHE_TTL = 60 * 60 
_embedder = None

def _rec_cache_key(user_id: int) -> str:
    return f"user_recommendations:{user_id}"


def invalidate_user_recommendations(user_id: int) -> None:
    cache.delete(_rec_cache_key(user_id))

def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu', model_kwargs={'low_cpu_mem_usage': False})
    return _embedder

def build_profile_text(profile) -> str:
    """
    Deterministic text representation of a user profile.
    Change this → bump reembed_all_profiles to keep vectors consistent.
    """
    parts = [
        profile.field_of_study or "",
        profile.bio or "",
        profile.preferred_scholarship_types or "",
        profile.preferred_countries or "",
        # Add more structured fields here as the model grows, e.g.:
        # profile.career_goals or "",
        # profile.achievements or "",
    ]
    return ". ".join(p.strip() for p in parts if p.strip())

def build_scholarship_text(scholarship) -> str:
    """
    Deterministic text representation of a scholarship.
    Handles list-type fields (JSONField arrays) gracefully.
    """
    def listify(val) -> str:
        if isinstance(val, list):
            return " ".join(str(v) for v in val)
        return str(val) if val else ""

    parts = [
        scholarship.title or "",
        scholarship.description or "",
        listify(scholarship.eligibility),
        listify(scholarship.requirements),
    ]
    return ". ".join(p.strip() for p in parts if p.strip())

def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def generate_fingerprint(title, link):
    base = f"{title.lower().strip()}-{link}"
    return hashlib.sha256(base.encode()).hexdigest()
# Load model once globally (so it's not reloaded on every task)

def _text_cache_key(text: str) -> str:
    return "embedding_" + hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_text_embedding(text, ttl_seconds= 7 * 24 * 3600) -> Optional[List[float]]:
    """
    Returns a list[float] embedding for the given text.
    Uses Redis cache keyed by hash(text) to avoid recomputation.
    """
    if not text or not text.strip():
        return None

    key = _text_cache_key(text)
    embedding = cache.get(key)
    if embedding is not None:
        return embedding

    try:
        emb = get_embedder().encode(text, show_progress_bar=False).tolist()
    except Exception as exc:
        logger.exception(f"[Embedding] encode() failed for text='{text[:60]}…': {exc}")
        return None
    cache.set(key, emb, timeout=ttl_seconds)
    return emb

def send_admin_alert(subject: str, body: str):
    admin_email = getattr(settings, "ADMINS_EMAIL", None)
    if admin_email:
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [admin_email])
        except Exception:
            # don't fail pipeline if alert fails
            pass

def send_user_notification(user, subject: str, body: str):
    """
    Replace with your real notification (email, push, slack).
    For now: simple email if user.email exists.
    """
    if getattr(user, "email", None):
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception:
            pass

_openrouter_client = None
_groq_client = None
_gemini_configured = False

def _ensure_clients_configured():
    """Lazily initialize clients only when needed."""
    global _gemini_configured, _openrouter_client, _groq_client
    
    if not _gemini_configured:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        _gemini_configured = True

    if _openrouter_client is None:
        _openrouter_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY") or "dummy_key",
        )

    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY") or "dummy_key",
        )

async def generate_text(prompt, response_format="text", max_words=None):
    """
    Infrastructure layer: Attempts Gemini -> OpenRouter -> Groq.
    Returns parsed JSON dict if response_format="json", else string.
    """
    _ensure_clients_configured()
    providers = ["gemini", "openrouter", "groq"]
    
    for provider in providers:
        try:
            if provider == "gemini":
                model_name = "gemini-2.0-flash"
                kwargs = {}
                
                if response_format == "json":
                    model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
                else:
                    model = genai.GenerativeModel(model_name)
                    if max_words:
                        kwargs["generation_config"] = {"max_output_tokens": max_words * 6, "temperature": 0.75}
                
                response = await model.generate_content_async(prompt, **kwargs)
                return json.loads(response.text) if response_format == "json" else response.text.strip()

            elif provider == "openrouter":
                kwargs = {"model": "openrouter/auto", "messages": [{"role": "user", "content": prompt}]}
                if response_format == "json":
                    kwargs["response_format"] = {"type": "json_object"}
                if max_words:
                    kwargs["max_tokens"] = max_words * 6
                    
                response = await _openrouter_client.chat.completions.create(**kwargs)
                result = response.choices[0].message.content
                return json.loads(result) if response_format == "json" else result.strip()

            elif provider == "groq":
                kwargs = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}
                if response_format == "json":
                    kwargs["response_format"] = {"type": "json_object"}
                if max_words:
                    kwargs["max_tokens"] = max_words * 6
                    
                response = await _groq_client.chat.completions.create(**kwargs)
                result = response.choices[0].message.content
                return json.loads(result) if response_format == "json" else result.strip()

        except Exception as e:
            logger.warning(f"[LLM Fallback] {provider.upper()} failed: {str(e)}")
            continue

    logger.error("Critical: All LLM providers failed.")
    return {} if response_format == "json" else ""

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60   

def _rec_cache_key(user_id: int) -> str:
    return f"user_recommendations_{user_id}"

def get_cached_recommendations(user, top_n=20):
    from scholarships.models import Scholarship
    key = _rec_cache_key(user.id)
    cached = cache.get(key)
    if cached:
        return cached["results"]

    # 2. Get User Profile
    profile = getattr(user, "profile", None)
    if profile.embedding is None or len(profile.embedding) == 0:
        return _fallback_recommendations(user)

   
    scholarships = Scholarship.objects.filter(
        active=True
    ).exclude(
        id__in=_get_excluded_scholarships(user)
    ).order_by(
        CosineDistance('embedding', profile.embedding)
    )[:top_n]

    results = list(scholarships)

    # 4. Save to Cache
    cache.set(
        key,
        {"results": results, "cached_at": now().isoformat()},
        CACHE_TTL_SECONDS,
    )

    return results

CHUNK_WEIGHTS = {
    "career_goals":    0.30,
    "academic":        0.25,
    "research":        0.15,
    "leadership":      0.10,
    "extracurriculars":0.10,
    "bio":             0.10,
}


def get_multi_vector_recommendations(profile, top_n: int = 20) -> list:
    """
    Score scholarships against multiple profile chunk embeddings,
    weighted by how much each dimension typically matters for matching.
    Falls back to single-vector if chunks aren't ready.
    """
    from scholarships.models import ProfileChunk, Scholarship
    chunks = list(
        ProfileChunk.objects.filter(profile=profile)
        .exclude(embedding__isnull=True)
    )

    if not chunks:
        # Fall back to the existing single-vector approach
        return _fallback_recommendations(profile.user)

    excluded = _get_excluded_scholarships(profile.user)
    scholarships = list(
        Scholarship.objects.filter(active=True)
        .exclude(id__in=excluded)
        .exclude(embedding__isnull=True)
    )

    if not scholarships:
        return []

    # Score each scholarship against each chunk, weighted
    scores: dict[int, float] = {s.id: 0.0 for s in scholarships}

    for chunk in chunks:
        weight = CHUNK_WEIGHTS.get(chunk.chunk_type, 0.05)
        ranked = (
            Scholarship.objects.filter(id__in=scores.keys())
            .order_by(CosineDistance("embedding", chunk.embedding))
            .values_list("id", flat=True)
        )
        total = len(ranked)
        for rank, sid in enumerate(ranked):
            # Convert rank to a 0-1 score (1 = most similar)
            position_score = (total - rank) / total
            scores[sid] += weight * position_score

    # Sort by aggregate weighted score
    sorted_ids = sorted(scores, key=scores.__getitem__, reverse=True)[:top_n]

    # Preserve order from DB
    id_order = {sid: i for i, sid in enumerate(sorted_ids)}
    result = sorted(
        [s for s in scholarships if s.id in id_order],
        key=lambda s: id_order[s.id],
    )
    return result


# --- Helpers ---
def _get_excluded_scholarships(user):
    from scholarships.models import Bookmark, Application
    bookmarked = Bookmark.objects.filter(user=user).values_list("scholarship_id", flat=True)
    applied = Application.objects.filter(user=user).values_list("scholarship_id", flat=True)
    return list(bookmarked) + list(applied)


def _fallback_recommendations(user):
    from scholarships.models import Scholarship
    """Used if profile embedding not available"""
    profile = user.profile
    excluded = _get_excluded_scholarships(user)
    return (
        Scholarship.objects.filter(
            Q(level__in=profile.level.all()) | Q(tags__in=profile.tags.all())
        )
        .exclude(id__in=excluded)
        .annotate(match_count=Count("tags", filter=Q(tags__in=profile.tags.all())))
        .order_by("-match_count", "end_date")
        .distinct()[:10]
    )

logger = logging.getLogger(__name__)

"""
scholarship_extractor.py
─────────────────────────────────────────────────────────────────────────────
Single, reusable extraction engine shared by:
  • ScholarshipBatchSpider  (Scrapy spider)
  • extract_from_html()     (Django REST view / Chrome-extension endpoint)

Usage
─────
# Plain HTML string (view / Chrome extension)
extractor = ScholarshipExtractor(raw_html=html_str, url="https://example.com/scholarship")
title      = extractor.extract_title()
end_date   = extractor.extract_date("end")
...

# Scrapy response object (spider)
extractor = ScholarshipExtractor(scrapy_response=response)
title      = extractor.extract_title()
...
"""        

def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_bullet(text: str) -> str:
    text = re.sub(r"^[\d.\)\-*•►→➤]\s*", "", text.strip())
    return re.sub(r"^\w\)\s*", "", text).strip()


def _try_parse_date(raw: str) -> Optional[date]:
    if not raw or len(raw) < 4:
        return None
    try:
        dt = dateparser.parse(
            raw,
            settings={"STRICT_PARSING": False, "PREFER_DATES_FROM": "future"},
        )
        return dt.date() if dt else None
    except Exception:
        return None

_NAV_PHRASES = frozenset([
    "postgraduate scholarships", "undergraduate scholarships",
    "masters scholarships", "phd scholarships", "high school scholarships",
    "scholarships by level", "scholarships by country", "scholarships by field",
    "competitions", "fellowships", "training", "internships",
    "recent posts", "categories", "archives", "related posts",
    "read more", "learn more", "click here", "apply now",
    "home", "about", "contact", "privacy policy", "terms",
    "menu", "search", "navigation", "skip to content",
    "share", "tweet", "facebook", "print", "email",
    "all scholarships", "browse scholarships", "find scholarships",
    "scholarship search", "sign in", "my account", "dashboard",
    "back to top", "continue reading", "load more",
])

# Heading keywords that identify the right content sections
_ELIGIBILITY_HEADINGS = [
    "eligibility", "who can apply", "who should apply",
    "criteria", "qualifications", "requirements to apply",
    "eligible applicants", "who is eligible",
]
_REQUIREMENTS_HEADINGS = [
    "requirements", "documents required", "required documents",
    "what you need", "application documents", "documents needed",
    "how to apply", "application requirements", "what to submit",
]


def _is_navigation_item(text: str) -> bool:
    """Returns True if this text looks like a navigation/sidebar item."""
    t = _normalize(text)
    if t in _NAV_PHRASES:
        return True
    # Ends with "scholarships" alone (sidebar category links)
    if re.match(r"^[a-z\s]+ scholarships?$", t):
        return True
    # Very short items with no sentence structure are usually nav
    if len(t.split()) < 3 and not any(c in t for c in [":", "("]):
        return True
    return False


class ScholarshipExtractor:
    def __init__(
        self,
        *,
        raw_html: Optional[str] = None,
        scrapy_response=None,
        url: Optional[str] = None,
    ):
        if scrapy_response is not None:
            self._response = scrapy_response
            self._sel = scrapy_response
            self.url = scrapy_response.url
            self.raw_html = scrapy_response.text
        elif raw_html is not None:
            self.raw_html = raw_html
            self._sel = Selector(text=raw_html)
            self._response = None
            self.url = url or ""
        else:
            raise ValueError("Provide either raw_html= or scrapy_response=")

        self._clean_text_cache: Optional[str] = None

    # ── low-level helpers ─────────────────────────────────────────────────────

    def css(self, query: str):
        return self._sel.css(query)

    @property
    def clean_text(self) -> str:
        if self._clean_text_cache is not None:
            return self._clean_text_cache
        try:
            text = trafilatura.extract(
                self.raw_html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )
            if text and len(text) > 200:
                self._clean_text_cache = text
                return text
        except Exception:
            pass

        content_selectors = [
            "article", ".entry-content", ".post-content",
            ".article-content", "main", "#content",
            "div[class*='content']", "div[class*='article']",
        ]
        for sel in content_selectors:
            text = self._extract_text_excluding_noise(self.css(sel))
            if text and len(text) > 500:
                self._clean_text_cache = text
                return text

        text = self._extract_text_excluding_noise(self.css("body"))
        self._clean_text_cache = text or ""
        return self._clean_text_cache

    def _extract_text_excluding_noise(self, selector) -> str:
        try:
            clean_xpath = """
                descendant-or-self::text()
                [not(ancestor::script)]
                [not(ancestor::style)]
                [not(ancestor::nav)]
                [not(ancestor::header)]
                [not(ancestor::footer)]
                [not(ancestor::aside)]
                [not(ancestor::div[contains(@class,'related')])]
                [not(ancestor::div[contains(@class,'sidebar')])]
                [not(ancestor::div[contains(@class,'widget')])]
                [not(ancestor::div[contains(@class,'comments')])]
                [not(ancestor::div[contains(@class,'menu')])]
                [not(ancestor::div[contains(@class,'nav')])]
                [not(ancestor::ul[contains(@class,'nav')])]
                [not(ancestor::ul[contains(@class,'menu')])]
            """
            texts = selector.xpath(clean_xpath).getall()
            joined = " ".join(t.strip() for t in texts if t.strip())
            return re.sub(r"\s+", " ", joined).strip()
        except Exception:
            try:
                return selector.xpath("string(.)").get() or ""
            except Exception:
                return ""

    def _section_text(self, css_selector: Optional[str]) -> Optional[str]:
        if not css_selector:
            return None
        clean = re.sub(r"::(text|attr\([^)]+\))", "", css_selector).strip()
        try:
            el = self.css(clean).get()
            if not el:
                return None
            sel = Selector(text=el)
            texts = sel.css("::text").getall()
            text = " ".join(t.strip() for t in texts if t.strip())
            if not text:
                text = sel.xpath("string(.)").get() or ""
            return text.strip() or None
        except Exception:
            return None

    # ── Semantic section finder ───────────────────────────────────────────────

    def _find_semantic_section(self, heading_keywords: list[str]) -> Optional[str]:
        """
        Find the content section whose heading matches one of the keywords.
        Returns the combined text of list items / paragraphs inside that section,
        guaranteed NOT to be navigation content.

        Strategy:
        1. Find a heading (h2/h3/h4/dt/strong/th) whose text matches a keyword.
        2. Walk forward siblings to collect li/p/dd text until the next heading.
        3. Return None if nothing substantive is found.
        """
        # All headings on the page
        heading_sel = "h1, h2, h3, h4, h5, dt, th, strong, [class*='heading'], [class*='title']"

        for heading_el in self.css(heading_sel):
            heading_text = _normalize(heading_el.xpath("string(.)").get() or "")
            if not any(kw in heading_text for kw in heading_keywords):
                continue

            # Found a matching heading — collect following content
            # Try parent container first
            parent_html = heading_el.xpath("..").get() or ""
            if not parent_html:
                continue

            parent_sel = Selector(text=parent_html)

            # Collect li items from the parent
            items = []
            for li in parent_sel.css("li"):
                text = li.xpath("string(.)").get(default="").strip()
                if text and not _is_navigation_item(text):
                    items.append(text)

            if items:
                return "\n".join(items)

            # Fallback: collect paragraphs
            for p in parent_sel.css("p"):
                text = p.xpath("string(.)").get(default="").strip()
                if len(text) > 20 and not _is_navigation_item(text):
                    items.append(text)

            if items:
                return "\n".join(items)

        return None

    def _find_content_list(self, heading_keywords: list[str], validator) -> list[str]:
        """
        Find list items under a semantic heading and validate each with `validator`.
        Falls back to searching clean_text with regex.
        Does NOT fall back to bare `ul li` (navigation poison risk).
        """
        results = []

        section_text = self._find_semantic_section(heading_keywords)
        if section_text:
            for line in re.split(r"[\n;•►→➤]", section_text):
                line = _clean_bullet(line).strip()
                if validator(line) and not _is_navigation_item(line):
                    results.append(line)
            if results:
                return results

        # Try class-targeted selectors only (NOT bare ul li)
        targeted_selectors = [
            f"[class*='{kw.split()[0]}'] li"
            for kw in heading_keywords
            if kw.split()[0] not in ("who", "what", "how")
        ]
        for sel in targeted_selectors:
            for el in self.css(sel):
                text = el.xpath("string(.)").get(default="").strip()
                if validator(text) and not _is_navigation_item(text):
                    results.append(text)
                    if len(results) >= 10:
                        break
            if results:
                return results

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # 1. TITLE
    # ─────────────────────────────────────────────────────────────────────────

    def extract_title(self, css_selector: Optional[str] = None) -> str:
        if css_selector:
            text = self._section_text(css_selector)
            if text and len(text.strip()) > 5:
                return text.strip()[:255]

        for sel in ["h1", ".entry-title", ".post-title", ".scholarship-title",
                    "[class*='title']", "[class*='heading']"]:
            title = self.css(f"{sel}::text").get()
            if title and len(title.strip()) > 5:
                title = title.split("|")[0].split(" - ")[0].strip()
                if not _is_navigation_item(title):
                    return title[:255]

        page_title = self.css("title::text").get()
        if page_title:
            return page_title.split("|")[0].strip()[:255]

        return "Scholarship Title Not Found"

    # ─────────────────────────────────────────────────────────────────────────
    # 2. DESCRIPTION
    # ─────────────────────────────────────────────────────────────────────────

    def extract_description(self, css_selector: Optional[str] = None) -> str:
        if css_selector:
            text = self._section_text(css_selector)
            if text and len(text) > 50:
                return text

        parts: list[str] = []

        meta = self.css('meta[name="description"]::attr(content)').get()
        if meta and len(meta) > 50:
            parts.append(meta.strip())

        skip = {"home", "menu", "navigation", "copyright", "privacy", "cookie",
                "subscribe", "newsletter", "advertisement"}
        for p in self.css("article p, .entry-content p, .post-content p, main p")[:8]:
            text = p.xpath("string(.)").get(default="").strip()
            if len(text) > 60 and not any(w in text.lower() for w in skip):
                parts.append(text)
                if len(parts) >= 3:
                    break

        if not parts:
            for p in self.css("p")[:6]:
                text = p.xpath("string(.)").get(default="").strip()
                if len(text) > 60 and not any(w in text.lower() for w in skip):
                    parts.append(text)
                    if len(parts) >= 2:
                        break

        if not parts:
            for sel in [".entry-content", ".post-content", ".article-content", "article", "main"]:
                text = self.css(sel).xpath("string(.)").get()
                if text and len(text.strip()) > 100:
                    parts.append(text.strip()[:600])
                    break

        if parts:
            return re.sub(r"\s+", " ", " ".join(parts))
        return "No description available"

    # ─────────────────────────────────────────────────────────────────────────
    # 3. REWARD
    # ─────────────────────────────────────────────────────────────────────────

    def extract_reward(self, css_selector: Optional[str] = None) -> str:
        if css_selector:
            text = self._section_text(css_selector)
            if text:
                return text

        page_text = self.clean_text

        naira  = [r"₦\s*([0-9,]+(?:\.[0-9]{2})?)", r"N\s*([0-9,]+(?:\.[0-9]{2})?)",
                  r"([0-9,]+(?:\.[0-9]{2})?)\s*naira"]
        usd    = [r"\$\s*([0-9,]+(?:\.[0-9]{2})?)",
                  r"([0-9,]+(?:\.[0-9]{2})?)\s*(?:USD|dollars?)"]
        gen    = [r"worth\s*(?:of\s*)?₦?\$?\s*([0-9,]+)",
                  r"value\s*(?:of\s*)?₦?\$?\s*([0-9,]+)",
                  r"amount\s*(?:of\s*)?₦?\$?\s*([0-9,]+)"]

        for group, prefix in [(naira, "₦"), (usd, "$"), (gen, "")]:
            for pattern in group:
                for match in re.finditer(pattern, page_text, re.IGNORECASE):
                    raw = match.group(1) if match.lastindex else match.group(0)
                    if isinstance(raw, tuple):
                        raw = next((x for x in raw if x), "")
                    try:
                        if float(raw.replace(",", "")) > 1000:
                            return f"{prefix}{raw}"
                    except (ValueError, AttributeError):
                        continue

        for kw in ["tuition", "allowance", "stipend", "support", "funding",
                   "full scholarship", "fully funded"]:
            if kw in page_text.lower():
                return f"Educational {kw}"

        return "Amount not specified"

    # ─────────────────────────────────────────────────────────────────────────
    # 4. DATES
    # ─────────────────────────────────────────────────────────────────────────

    def extract_date(
        self,
        date_type: str = "end",
        css_selector: Optional[str] = None,
    ) -> Optional[date]:
        if css_selector:
            raw = self._section_text(css_selector)
            if raw:
                parsed = _try_parse_date(raw)
                if parsed:
                    return parsed

        return self._date_from_text(self.clean_text, date_type)

    def _date_from_text(self, text: str, date_type: str) -> Optional[date]:
        if date_type == "start":
            patterns = [
                r"application\s*(?:opens?|starts?)[:\s]*([^.!?\n]+)",
                r"opening\s*date[:\s]*([^.!?\n]+)",
                r"start\s*date[:\s]*([^.!?\n]+)",
                r"begins?[:\s]*([^.!?\n]+)",
                r"from[:\s]*([^.!?\n]+?)(?:\s*to\s*|\s*-\s*)",
                r"available\s*from[:\s]*([^.!?\n]+)",
            ]
        else:
            patterns = [
                r"deadline[:\s]*([^.!?\n]+)",
                r"due date[:\s]*([^.!?\n]+)",
                r"closing date[:\s]*([^.!?\n]+)",
                r"last date[:\s]*([^.!?\n]+)",
                r"application closes?[:\s]*([^.!?\n]+)",
                r"expires?[:\s]*([^.!?\n]+)",
                r"close[sd]?\s*on[:\s]*([^.!?\n]+)",
                r"submit\s*by[:\s]*([^.!?\n]+)",
            ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                parsed = _try_parse_date(match.group(1).strip())
                if parsed:
                    return parsed
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # 5. ELIGIBILITY
    # ─────────────────────────────────────────────────────────────────────────

    def extract_eligibility(
        self,
        css_selector: Optional[str] = None,
        fallback_text: Optional[str] = None,
    ) -> list[str]:
        results: list[str] = []

        # ── A. Targeted CSS selector ──────────────────────────────────────────
        if css_selector:
            raw = self._section_text(css_selector)
            if raw:
                for header in ["Eligibility:", "Who can apply:", "Criteria:"]:
                    raw = raw.replace(header, "")
                for part in re.split(r"[\n;•►→➤]", raw):
                    part = _clean_bullet(part).strip()
                    if self._is_eligibility(part) and not _is_navigation_item(part):
                        results.append(part)
            if results:
                return self._clean_items(results)

        # ── B. Semantic section detection (navigation-safe) ───────────────────
        results = self._find_content_list(_ELIGIBILITY_HEADINGS, self._is_eligibility)
        if results:
            return self._clean_items(results)

        # ── C. Regex over clean_text ──────────────────────────────────────────
        page_text = fallback_text or self.clean_text
        patterns = [
            r"eligibility[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
            r"eligible\s*(?:candidates?|applicants?)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
            r"who\s*can\s*apply[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
            r"criteria[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
            r"qualifications?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, page_text, re.IGNORECASE | re.MULTILINE):
                chunk = m.group(1).strip()
                items = self._split_items(chunk, self._is_eligibility)
                items = [i for i in items if not _is_navigation_item(i)]
                results.extend(items)
                if results:
                    break
            if results:
                break

        # ── D. Structured keyword fallback ────────────────────────────────────
        if not results:
            results = self._common_eligibility(page_text)

        cleaned = self._clean_items(results)

        # ── E. Validation gate — if still looks like nav, return empty ─────────
        # Signal to caller (spider / process_new_submission) that LLM is needed
        if not cleaned or all(_is_navigation_item(r) for r in cleaned):
            return []   # Empty → QualityCheck will flag → LLM fires

        return cleaned

    # ─────────────────────────────────────────────────────────────────────────
    # 6. REQUIREMENTS
    # ─────────────────────────────────────────────────────────────────────────

    def extract_requirements(
        self,
        css_selector: Optional[str] = None,
        fallback_text: Optional[str] = None,
    ) -> list[str]:
        results: list[str] = []

        # ── A. Targeted CSS selector ──────────────────────────────────────────
        if css_selector:
            raw = self._section_text(css_selector)
            if raw:
                for header in ["Requirements:", "Documents Required:", "What you need:"]:
                    raw = raw.replace(header, "")
                for part in re.split(r"[\n;•►→➤]", raw):
                    part = _clean_bullet(part).strip()
                    if self._is_requirement(part) and not _is_navigation_item(part):
                        results.append(part)
            if results:
                return self._clean_items(results)

        # ── B. Semantic section detection ─────────────────────────────────────
        results = self._find_content_list(_REQUIREMENTS_HEADINGS, self._is_requirement)
        if results:
            return self._clean_items(results)

        # ── C. Regex over clean_text ──────────────────────────────────────────
        page_text = fallback_text or self.clean_text
        patterns = [
            r"requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
            r"documents?\s*(?:required|needed)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
            r"application\s*requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
            r"must\s*(?:provide|submit|include)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*){0,5})",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, page_text, re.IGNORECASE | re.MULTILINE):
                chunk = m.group(1).strip()
                items = self._split_items(chunk, self._is_requirement)
                items = [i for i in items if not _is_navigation_item(i)]
                results.extend(items)
                if results:
                    break
            if results:
                break

        # ── D. Keyword fallback ───────────────────────────────────────────────
        if not results:
            results = self._common_requirements(page_text)

        cleaned = self._clean_items(results)

        if not cleaned or all(_is_navigation_item(r) for r in cleaned):
            return []   # Empty → LLM fires

        return cleaned

    # ─────────────────────────────────────────────────────────────────────────
    # 7. LEVELS
    # ─────────────────────────────────────────────────────────────────────────

    def extract_levels(self, css_selector: Optional[str] = None, extra_text: str = "") -> list[str]:
        if css_selector:
            extracted = self.css(css_selector).getall()
            cleaned = [x.strip().lower() for x in extracted if x.strip()]
            if cleaned:
                return cleaned

        title_text = (self.css("title::text").get() or "").lower()
        meta_desc  = (self.css('meta[name="description"]::attr(content)').get() or "").lower()
        all_text   = f"{self.clean_text} {title_text} {meta_desc} {extra_text}".lower()

        level_keywords = {
            "highschool":    ["secondary school", "high school", "ssce", "waec", "neco", "a-level", "k12"],
            "undergraduate": ["undergraduate", "bachelor", "bsc", "ba ", "first degree", "college student"],
            "postgraduate":  ["postgraduate", "masters", "msc", "ma ", "mphil", "graduate school"],
            "phd":           ["phd", "doctorate", "doctoral", "dphil", "research degree"],
        }
        detected = {lvl for lvl, kws in level_keywords.items() if any(k in all_text for k in kws)}
        return list(detected) or ["unspecified"]

    # ─────────────────────────────────────────────────────────────────────────
    # 8. TAGS
    # ─────────────────────────────────────────────────────────────────────────

    def extract_tags(self, css_selector: Optional[str] = None, extra_text: str = "") -> list[str]:
        if css_selector:
            extracted = self.css(css_selector).getall()
            cleaned = [x.strip().lower() for x in extracted if x.strip()]
            if cleaned:
                return cleaned

        title_text = _normalize(self.css("title::text").get() or "")
        all_text   = _normalize(f"{self.clean_text} {title_text} {extra_text}")

        tag_keywords = {
            "international": ["international", "global", "worldwide", "abroad", "foreign"],
            "women":         ["women", "female", "girls"],
            "stem":          ["stem", "engineering", "science"],
            "merit":         ["merit", "academic excellence", "outstanding", "scholarly"],
            "need":          ["need", "financial aid", "low income", "need-based"],
        }

        tags: set[str] = set()
        for tag, kws in tag_keywords.items():
            if any(kw in all_text for kw in kws):
                tags.add(tag)

        meta_kws = self.css('meta[name="keywords"]::attr(content)').get()
        if meta_kws:
            for mt in _normalize(meta_kws).split(","):
                mt = mt.strip()
                for key in tag_keywords:
                    if get_close_matches(mt, [key], n=1, cutoff=0.8):
                        tags.add(key)

        # Only use tag/category selectors, not generic nav
        for sel in [".tags a", ".categories a", ".tag", ".category",
                    "[class*='tag']", "[class*='category']"]:
            for el in self.css(sel)[:5]:
                tag_text = _normalize(el.xpath("string(.)").get(default=""))
                for key, kws in tag_keywords.items():
                    if tag_text in kws or get_close_matches(tag_text, kws, n=1, cutoff=0.8):
                        tags.add(key)

        return list(tags) or ["general"]

    # ─────────────────────────────────────────────────────────────────────────
    # Private validators & utilities
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_eligibility(text: str) -> bool:
        if not text or _is_navigation_item(text):
            return False
        # Must have at least 5 words to be a real criterion
        if len(text.split()) < 5:
            return False
        keywords = [
            "citizen", "nationality", "age", "year old", "year of age",
            "grade", "gpa", "cgpa", "score",
            "undergraduate", "postgraduate", "graduate", "student",
            "enrolled", "admitted", "applicant",
            "resident", "income", "family",
            "female", "male", "gender",
            "minority", "disability", "field of study",
            "department", "faculty", "university", "college",
            "must be", "must have", "should be", "should have",
            "open to", "available to", "eligible",
        ]
        t = text.lower()
        # Require a keyword AND that it reads like a criterion (not a nav label)
        has_keyword = any(k in t for k in keywords)
        has_verb    = any(v in t for v in ["must", "should", "need", "require",
                                            "open", "eligible", "have", "be a", "be an"])
        return (has_keyword or has_verb) and 15 < len(text) < 300

    @staticmethod
    def _is_requirement(text: str) -> bool:
        if not text or _is_navigation_item(text):
            return False
        if len(text.split()) < 4:
            return False
        keywords = [
            "transcript", "certificate", "cv", "resume", "letter",
            "essay", "statement", "recommendation", "reference",
            "passport", "photo", "photograph",
            "application form", "birth certificate", "identification",
            "academic record", "degree", "diploma",
            "ssce", "waec", "jamb", "neco",
            "bank statement", "financial", "medical report",
            "upload", "submit", "attach", "provide",
            "official", "certified", "notarized",
            "two copies", "three copies",
        ]
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 300

    @staticmethod
    def _split_items(text: str, validator) -> list[str]:
        for delimiter in ["\n", ";", "•", "►", "→", "➤"]:
            if delimiter in text:
                return [_clean_bullet(p).strip()
                        for p in text.split(delimiter)
                        if validator(_clean_bullet(p).strip())]
        sentences = re.split(r"[.!?]", text)
        return [s.strip() for s in sentences if validator(s.strip())] or [text.strip()]

    @staticmethod
    def _clean_items(items: list[str], max_items: int = 10) -> list[str]:
        cleaned = []
        for item in items[:max_items * 2]:
            item = _clean_bullet(item)
            if 12 < len(item) < 300 and not _is_navigation_item(item):
                cleaned.append(item[0].upper() + item[1:] if item else item)
        # Deduplicate preserving order
        seen = set()
        deduped = []
        for item in cleaned:
            key = _normalize(item)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped[:max_items]

    @staticmethod
    def _common_eligibility(page_text: str) -> list[str]:
        eligibility: list[str] = []
        t = page_text.lower()

        age = re.search(
            r"(?:age|years?)\s*(?:between|from|of)?\s*(\d+)(?:\s*(?:to|and|-)\s*(\d+))?",
            t
        )
        if age:
            if age.group(2):
                eligibility.append(f"Age between {age.group(1)} and {age.group(2)} years")
            else:
                eligibility.append(f"Age {age.group(1)} years or above")

        mapping = [
            ("undergraduate", "Must be an undergraduate student"),
            ("postgraduate",  "Must be a postgraduate student"),
            ("international", "Open to international students"),
        ]
        for kw, label in mapping:
            if kw in t:
                eligibility.append(label)

        if "nigerian" in t and "citizen" in t:
            eligibility.append("Must be a Nigerian citizen")

        gpa = re.search(r"(?:gpa|cgpa)\s*(?:of\s*)?(\d+\.?\d*)", t)
        if gpa:
            eligibility.append(f"Minimum GPA/CGPA of {gpa.group(1)}")

        if "female only" in t or "women only" in t:
            eligibility.append("Female students only")
        elif "male only" in t:
            eligibility.append("Male students only")

        return eligibility

    @staticmethod
    def _common_requirements(page_text: str) -> list[str]:
        t = page_text.lower()
        patterns = {
            "Academic Transcript":      ["transcript", "academic record"],
            "CV or Resume":             ["cv", "resume", "curriculum vitae"],
            "Passport Photograph":      ["passport photo", "recent photo", "passport photograph"],
            "Birth Certificate":        ["birth certificate"],
            "Letter of Recommendation": ["recommendation letter", "reference letter", "letter of recommendation"],
            "Statement of Purpose":     ["statement of purpose", "personal statement", "motivation letter"],
            "Application Form":         ["application form", "completed form"],
            "Academic Certificates":    ["academic certificate", "degree certificate"],
            "Valid ID / Passport":      ["national id", "valid passport", "identification document"],
        }
        return [name for name, kws in patterns.items() if any(k in t for k in kws)]

    

# SiteConfig.objects.create(
#     name="Scholarship Region",
#     base_url="https://www.scholarshipregion.com",
#     list_url="https://www.scholarshipregion.com/category/scholarships/",
#     list_item_selector=".td_module_wrap",
#     title_selector=".entry-title a::text",
#     link_selector=".entry-title a::attr(href)",
#     description_selector=".td-post-content p",
#     eligibility_selector=".elementor-widget-text-editor ul li",
#     requirements_selector=".elementor-widget-text-editor ul li",
#     deadline_selector="h4:contains('Deadline')::text",
#     start_date_selector="",
#     reward_selector="",
#     level_selector="",
#     tag_selector=".td-post-category a::text",
#     active=True,
# )
