import random
import string
import hashlib
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache 
import numpy as np
from django.db.models import Count, Q
from django.utils.timezone import now
from sklearn.metrics.pairwise import cosine_similarity
from pgvector.django import CosineDistance
from typing import Optional, List
import re
import logging
import dateparser
import trafilatura
from parsel import Selector
from difflib import get_close_matches
from __future__ import annotations

import re
from datetime import date
from difflib import get_close_matches
from typing import Optional

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
        _embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
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



CACHE_TTL_SECONDS = 7 * 24 * 60 * 60   

def _rec_cache_key(user_id: int) -> str:
    return f"user_recommendations_{user_id}"

# def get_cached_recommendations(user, top_n=20):
#     from scholarships.models import Scholarship
#     key = _rec_cache_key(user.id)
#     cached = cache.get(key)

#     if cached:
#         return cached["results"]

#     profile = getattr(user, "profile", None)
#     if not profile or not profile.embedding:
#         return _fallback_recommendations(user)

#     user_vec = np.array(profile.embedding, dtype=float)

#     scholarships = Scholarship.objects.filter(
#         active=True, embedding__isnull=False
#     ).exclude(
#         id__in=_get_excluded_scholarships(user)
#     )

#     # Compute cosine similarity
#     results = []
#     for s in scholarships:
#         try:
#             sim = cosine_similarity([user_vec], [np.array(s.embedding, dtype=float)])[0][0]
#             results.append((s, sim))
#         except Exception as e:
#             print(e)
#             continue

#     results = sorted(results, key=lambda x: x[1], reverse=True)[:top_n]
#     scholarships = [s for s, _ in results]

#     cache.set(
#         key,
#         {"results": scholarships, "cached_at": now().isoformat()},
#         CACHE_TTL_SECONDS,
#     )

#     return scholarships

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


# Core class

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
            self._sel = scrapy_response          # Scrapy Response IS a Selector
            self.url = scrapy_response.url
            self.raw_html = scrapy_response.text
        elif raw_html is not None:
            self.raw_html = raw_html
            self._sel = Selector(text=raw_html)  # parsel Selector
            self._response = None
            self.url = url or ""
        else:
            raise ValueError("Provide either raw_html= or scrapy_response=")

        self._clean_text_cache: Optional[str] = None  # lazy

    # ── low-level helpers ─────────────────────────────────────────────────────

    def css(self, query: str):
        return self._sel.css(query)

    @property
    def clean_text(self) -> str:
        """Cached, noise-stripped body text (trafilatura → CSS fallback)."""
        if self._clean_text_cache is not None:
            return self._clean_text_cache
        try:
            text = trafilatura.extract(self.raw_html)
            if text and len(text) > 200:
                self._clean_text_cache = text
                return text
        except Exception:
            pass

        content_selectors = [
            "article", ".entry-content", ".post-content",
            ".article-content", "main", "#content", "div[class*='content']",
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
                [not(ancestor::footer)]
                [not(ancestor::aside)]
                [not(ancestor::div[contains(@class,'related')])]
                [not(ancestor::div[contains(@class,'sidebar')])]
                [not(ancestor::div[contains(@class,'widget')])]
                [not(ancestor::div[contains(@class,'comments')])]
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
        """
        Extract combined visible text from the first element matching a CSS
        selector.  Handles ::text / ::attr suffixes gracefully.
        """
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

    # ─────────────────────────────────────────────────────────────────────────
    # 1. TITLE
    # ─────────────────────────────────────────────────────────────────────────

    def extract_title(self, css_selector: Optional[str] = None) -> str:
        if css_selector:
            text = self._section_text(css_selector)
            if text:
                return text[:255]

        for sel in ["h1", ".entry-title", ".post-title", ".scholarship-title", "[class*='title']"]:
            title = self.css(f"{sel}::text").get()
            if title and len(title.strip()) > 5:
                title = title.split("|")[0].split(" - ")[0].strip()
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
            if text:
                return text

        parts: list[str] = []

        meta = self.css('meta[name="description"]::attr(content)').get()
        if meta and len(meta) > 50:
            parts.append(meta.strip())

        skip = {"home", "menu", "navigation", "copyright", "privacy", "cookie"}
        for p in self.css("p")[:5]:
            text = p.xpath("string(.)").get(default="").strip()
            if len(text) > 50 and not any(w in text.lower() for w in skip):
                parts.append(text)
                if len(parts) >= 3:
                    break

        if not parts:
            for sel in [".entry-content", ".post-content", ".article-content", "article"]:
                text = self.css(sel).xpath("string(.)").get()
                if text and len(text.strip()) > 100:
                    parts.append(text.strip()[:500])
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

        naira = [r"₦\s*([0-9,]+(?:\.[0-9]{2})?)", r"N\s*([0-9,]+(?:\.[0-9]{2})?)", r"([0-9,]+(?:\.[0-9]{2})?)\s*naira"]
        usd   = [r"\$\s*([0-9,]+(?:\.[0-9]{2})?)", r"([0-9,]+(?:\.[0-9]{2})?)\s*(?:USD|dollars?)"]
        gen   = [r"worth\s*(?:of\s*)?₦?\$?\s*([0-9,]+)", r"value\s*(?:of\s*)?₦?\$?\s*([0-9,]+)", r"amount\s*(?:of\s*)?₦?\$?\s*([0-9,]+)"]

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

        for kw in ["tuition", "allowance", "stipend", "support", "funding", "full scholarship"]:
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
        """date_type: 'end' (deadline) or 'start'."""
        # Try CSS selector first
        if css_selector:
            raw = self._section_text(css_selector)
            if raw:
                parsed = _try_parse_date(raw)
                if parsed:
                    return parsed

        # Regex over clean text
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
                r"registration\s*(?:opens?|starts?)[:\s]*([^.!?\n]+)",
            ]
        else:
            patterns = [
                r"deadline[:\s]*([^.!?\n]+)",
                r"due date[:\s]*([^.!?\n]+)",
                r"closing date[:\s]*([^.!?\n]+)",
                r"last date[:\s]*([^.!?\n]+)",
                r"application closes[:\s]*([^.!?\n]+)",
                r"expires?[:\s]*([^.!?\n]+)",
                r"until[:\s]*([^.!?\n]+)",
                r"by[:\s]*([^.!?\n]+)",
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

        # From targeted selector
        if css_selector:
            raw = self._section_text(css_selector)
            if raw:
                for header in ["Eligibility:", "Who can apply:", "Criteria:"]:
                    raw = raw.replace(header, "")
                for part in re.split(r"[\n;•►→➤]", raw):
                    if self._is_eligibility(part.strip()):
                        results.append(part.strip())

        # From structured list elements
        if not results:
            list_selectors = [
                ".eligibility li", ".criteria li",
                "[class*='eligibility'] li", "[class*='criteria'] li",
                "[class*='qualification'] li", "ul li", "ol li",
            ]
            for sel in list_selectors:
                for el in self.css(sel):
                    text = el.xpath("string(.)").get(default="").strip()
                    if self._is_eligibility(text):
                        results.append(text)
                        if len(results) >= 10:
                            break
                if results:
                    break

        # Regex patterns over page text
        if not results:
            page_text = fallback_text or self.clean_text
            patterns = [
                r"eligibility[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"eligible\s*(?:candidates?|applicants?)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"who\s*can\s*apply[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"criteria[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"qualifications?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"must\s*be[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
            ]
            for pattern in patterns:
                for m in re.finditer(pattern, page_text, re.IGNORECASE | re.MULTILINE):
                    chunk = m.group(1).strip()
                    items = self._split_items(chunk, self._is_eligibility)
                    results.extend(items)
                    if results:
                        break
                if results:
                    break

        # Keyword fallback
        if not results:
            results = self._common_eligibility(fallback_text or self.clean_text)

        return self._clean_items(results) or ["Eligibility criteria not specified"]

    # ─────────────────────────────────────────────────────────────────────────
    # 6. REQUIREMENTS
    # ─────────────────────────────────────────────────────────────────────────

    def extract_requirements(
        self,
        css_selector: Optional[str] = None,
        fallback_text: Optional[str] = None,
    ) -> list[str]:
        results: list[str] = []

        if css_selector:
            raw = self._section_text(css_selector)
            if raw:
                for header in ["Requirements:", "Documents Required:", "What you need:"]:
                    raw = raw.replace(header, "")
                for part in re.split(r"[\n;•►→➤]", raw):
                    if self._is_requirement(part.strip()):
                        results.append(part.strip())

        if not results:
            list_selectors = [
                ".requirements li", ".documents li",
                "[class*='requirement'] li", "[class*='document'] li",
                "ul li", "ol li",
            ]
            for sel in list_selectors:
                for el in self.css(sel):
                    text = el.xpath("string(.)").get(default="").strip()
                    if self._is_requirement(text):
                        results.append(text)
                        if len(results) >= 10:
                            break
                if results:
                    break

        if not results:
            page_text = fallback_text or self.clean_text
            patterns = [
                r"requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"documents?\s*(?:required|needed)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"application\s*requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"needed\s*documents?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"submit[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
                r"must\s*(?:provide|submit|include)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)",
            ]
            for pattern in patterns:
                for m in re.finditer(pattern, page_text, re.IGNORECASE | re.MULTILINE):
                    chunk = m.group(1).strip()
                    items = self._split_items(chunk, self._is_requirement)
                    results.extend(items)
                    if results:
                        break
                if results:
                    break

        if not results:
            results = self._common_requirements(fallback_text or self.clean_text)

        return self._clean_items(results) or ["Requirements not specified"]

    # ─────────────────────────────────────────────────────────────────────────
    # 7. LEVELS
    # ─────────────────────────────────────────────────────────────────────────

    def extract_levels(
        self,
        css_selector: Optional[str] = None,
        extra_text: str = "",
    ) -> list[str]:
        if css_selector:
            extracted = self.css(css_selector).getall()
            cleaned = [x.strip().lower() for x in extracted if x.strip()]
            if cleaned:
                return cleaned

        title_text = (self.css("title::text").get() or "").lower()
        meta_desc  = (self.css('meta[name="description"]::attr(content)').get() or "").lower()
        all_text   = f"{self.clean_text} {title_text} {meta_desc} {extra_text}".lower()

        level_keywords = {
            "highschool":    ["secondary school", "high school", "ssce", "waec", "neco", "alevel", "k12"],
            "undergraduate": ["undergraduate", "bachelor", "bsc", "ba", "first degree", "college student"],
            "postgraduate":  ["postgraduate", "masters", "msc", "ma", "mphil", "graduate school"],
            "phd":           ["phd", "doctorate", "doctoral", "dphil", "research degree"],
        }
        detected = {lvl for lvl, kws in level_keywords.items() if any(k in all_text for k in kws)}
        return list(detected) or ["unspecified"]

    # ─────────────────────────────────────────────────────────────────────────
    # 8. TAGS
    # ─────────────────────────────────────────────────────────────────────────

    def extract_tags(
        self,
        css_selector: Optional[str] = None,
        extra_text: str = "",
    ) -> list[str]:
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

        for sel in [".tags a", ".categories a", ".tag", ".category", "[class*='tag']", "[class*='category']"]:
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
        keywords = [
            "citizen", "age", "year", "grade", "gpa", "cgpa", "score", "level",
            "undergraduate", "graduate", "student", "enrolled", "admitted",
            "nationality", "resident", "income", "family", "female", "male",
            "minority", "disability", "field of study", "department", "faculty",
            "university", "college",
        ]
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 200

    @staticmethod
    def _is_requirement(text: str) -> bool:
        keywords = [
            "transcript", "certificate", "cv", "resume", "letter", "essay",
            "statement", "recommendation", "reference", "passport", "photo",
            "application form", "birth certificate", "identification",
            "academic record", "degree", "diploma", "ssce", "waec", "jamb",
            "bank statement", "financial", "medical report", "upload", "submit",
        ]
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 200

    @staticmethod
    def _split_items(text: str, validator) -> list[str]:
        for delimiter in ["\n", ";", "•", "►", "→", "➤"]:
            if delimiter in text:
                return [p.strip() for p in text.split(delimiter) if validator(p.strip())]
        sentences = re.split(r"[.!?]", text)
        return [s.strip() for s in sentences if validator(s.strip())] or [text.strip()]

    @staticmethod
    def _clean_items(items: list[str], max_items: int = 10) -> list[str]:
        cleaned = []
        for item in items[:max_items]:
            item = _clean_bullet(item)
            if 10 < len(item) < 200:
                cleaned.append(item.capitalize())
        return list(dict.fromkeys(cleaned))  # deduplicate, preserve order

    @staticmethod
    def _common_eligibility(page_text: str) -> list[str]:
        eligibility: list[str] = []
        t = page_text.lower()

        age = re.search(r"(?:age|years?)\s*(?:between|from)?\s*(\d+)(?:\s*(?:to|and|-)\s*(\d+))?", t)
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

        if "female only" in t:
            eligibility.append("Female students only")
        elif "male only" in t:
            eligibility.append("Male students only")

        return eligibility

    @staticmethod
    def _common_requirements(page_text: str) -> list[str]:
        t = page_text.lower()
        patterns = {
            "Academic Transcript":      ["transcript", "academic record"],
            "CV/Resume":                ["cv", "resume", "curriculum vitae"],
            "Passport Photograph":      ["passport photo", "recent photo"],
            "Birth Certificate":        ["birth certificate"],
            "Letter of Recommendation": ["recommendation letter", "reference letter"],
            "Statement of Purpose":     ["statement of purpose", "personal statement"],
            "Application Form":         ["application form", "completed form"],
            "Academic Certificates":    ["certificate", "degree certificate"],
            "Identification Document":  ["id card", "identification", "national id"],
        }
        return [name for name, kws in patterns.items() if any(k in t for k in kws)]    
    
    
# def get_cached_recommendations(user, top_n: int = 20):
#     key = _rec_cache_key(user.id)
#     cached = cache.get(key)
#     scholarships_updated_at = cache.get("scholarships_updated_at")

#     # --- Strategy B: freshness check ---
#     if cached and scholarships_updated_at:
#         cached_at = cached.get("cached_at")
#         if cached_at and cached_at < scholarships_updated_at:
#             cached = None  # force recompute

#     if cached:
#         return cached["results"]

#     # recompute
#     profile = getattr(user, "profile", None)
#     if not profile or not profile.embedding:
#         return []

#     user_vec = np.array(profile.embedding, dtype=float)
#     qs = Scholarship.objects.filter(embedding__isnull=False, active=True)

#     results = []
#     for s in qs:
#         sim = cosine_similarity([user_vec], [np.array(s.embedding, dtype=float)])[0][0]
#         results.append({"id": s.id, "score": float(sim)})

#     results = sorted(results, key=lambda r: r["score"], reverse=True)[:top_n]

#     # save cache with timestamp
#     cache.set(
#         key,
#         {"results": results, "cached_at": now().isoformat()},
#         CACHE_TTL_SECONDS,
#     )
#     return results

# def get_cached_recommendations(user, top_n=10):
#     key = _rec_cache_key(user.id)
#     cached = cache.get(key)
#     if cached is not None:
#         return cached

#     profile = getattr(user, 'profile', None)
#     if not profile or not profile.embedding:
#         return []

#     user_vec = np.array(profile.embedding, dtype=float)
#     qs = Scholarship.objects.filter(embedding__isnull=False, active=True)

#     results = []
#     for s in qs:
#         sim = cosine_similarity([user_vec], [np.array(s.embedding, dtype=float)])[0][0]
#         results.append({"id": s.id, "score": float(sim)})

#     results = sorted(results, key=lambda r: r['score'], reverse=True)[:top_n]
#     cache.set(key, results, CACHE_TTL_SECONDS)
#     return results

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
