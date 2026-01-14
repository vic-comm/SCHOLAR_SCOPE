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
from typing import Optional, List

_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu', model_kwargs={"low_cpu_mem_usage": False})
    return _embedder

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

    emb = get_embedder().encode(text).tolist()
    cache.set(key, emb, timeout=ttl_seconds)
    return emb

# def get_profile_embedding(profile):
#     model = SentenceTransformer('all-MiniLM-L6-v2')
#     text = f"{profile.field_of_study}. {profile.bio}. {profile.preferred_scholarship_types}. {profile.preferred_countries}"
#     return model.encode(text)

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



CACHE_TTL_SECONDS = 7 * 24 * 60 * 60   # 1 hour

def _rec_cache_key(user_id: int) -> str:
    return f"user_recommendations_{user_id}"

def get_cached_recommendations(user, top_n=20):
    from scholarships.models import Scholarship
    key = _rec_cache_key(user.id)
    cached = cache.get(key)

    if cached:
        return cached["results"]

    # 1️⃣ Get profile + embedding
    profile = getattr(user, "profile", None)
    if not profile or not profile.embedding:
        # fallback to tag/level match if embedding missing
        return _fallback_recommendations(user)

    user_vec = np.array(profile.embedding, dtype=float)

    # 2️⃣ Filter eligible scholarships
    scholarships = Scholarship.objects.filter(
        active=True, embedding__isnull=False
    ).exclude(
        id__in=_get_excluded_scholarships(user)
    )

    # 3️⃣ Compute cosine similarity
    results = []
    for s in scholarships:
        try:
            sim = cosine_similarity([user_vec], [np.array(s.embedding, dtype=float)])[0][0]
            results.append((s, sim))
        except Exception:
            continue

    # 4️⃣ Sort + limit
    results = sorted(results, key=lambda x: x[1], reverse=True)[:top_n]
    scholarships = [s for s, _ in results]

    # 5️⃣ Cache results
    cache.set(
        key,
        {"results": scholarships, "cached_at": now().isoformat()},
        CACHE_TTL_SECONDS,
    )

    return scholarships


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
