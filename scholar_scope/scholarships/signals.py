from django.db.models.signals import post_save
from .models import User, Profile
from django.dispatch import receiver
from scholarships.tasks import generate_profile_embedding, generate_scholarship_embedding
from .utils import get_text_embedding
from scholarships.models import Scholarship
from django.utils.timezone import now
from django.db import models
from scholarships.tasks import batch_invalidate_user_recommendations
from django.core.cache import cache
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        profile = Profile.objects.create(user=instance)
        if _profile_has_embeddable_text(profile):
            generate_profile_embedding.delay(profile_id=profile.id)


def _profile_has_embeddable_text(profile) -> bool:
    return bool(
        (profile.field_of_study or "").strip()
        or (profile.bio or "").strip()
        or (profile.preferred_scholarship_types or "").strip()
    )

@receiver(post_save, sender=Profile)
def reembed_profile_on_update(sender, instance, created, **kwargs):
    if not _profile_has_embeddable_text(instance):
        return
    generate_profile_embedding.delay(profile_id=instance.id)

@receiver(post_save, sender=Scholarship)
def embed_scholarship_on_create(sender, instance, created, **kwargs):
    if created:
       generate_scholarship_embedding.delay(scholarship_id=instance.id)

@receiver(post_save, sender=Scholarship)
def invalidate_caches_on_scholarship_save(sender, instance, created, **kwargs):
    """
    Strategy A + B combo:
    - A: selectively clear cache for users with overlapping tags/levels.
    - B: update global scholarship dataset timestamp.
    """

    # --- Strategy B: update global timestamp ---
    if created:
        cache.set("scholarships_updated_at", now().isoformat())

    # --- Strategy A: selective invalidation ---
    tag_ids   = _safe_m2m_ids(instance, "tags")
    level_ids = _safe_m2m_ids(instance, "level")

    if not tag_ids and not level_ids:
        return  # nothing to match on

    user_ids = list(
        Profile.objects.filter(
            models.Q(tags__in=tag_ids) | models.Q(level__in=level_ids)
        ).distinct().values_list("user_id", flat=True)
    )

    if not user_ids:
        return
    
    BATCH_SIZE = 500
    for i in range(0, len(user_ids), BATCH_SIZE):
        batch = user_ids[i : i + BATCH_SIZE]
        batch_invalidate_user_recommendations.delay(batch)


def _safe_m2m_ids(instance, field_name: str) -> list:
    """
    Safely read M2M IDs from a model instance.
    Returns an empty list if the field doesn't exist or the relation
    isn't yet set up (e.g. during migrations).
    """
    try:
        manager = getattr(instance, field_name, None)
        if manager is None:
            return []
        return list(manager.values_list("id", flat=True))
    except Exception:
        return []