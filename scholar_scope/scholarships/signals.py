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
        generate_profile_embedding.delay(profile_id=profile.id)


@receiver(post_save, sender=Scholarship)
def create_embeddings(sender, instance, created, **kwargs):
    if created:
       generate_scholarship_embedding.delay(scholarship_id=instance.id)

@receiver(post_save, sender=Scholarship)
def scholarship_post_save_invalidate(sender, instance, created, **kwargs):
    """
    Strategy A + B combo:
    - A: selectively clear cache for users with overlapping tags/levels.
    - B: update global scholarship dataset timestamp.
    """

    # --- Strategy B: update global timestamp ---
    if created:
        cache.set("scholarships_updated_at", now().isoformat())

    # --- Strategy A: selective invalidation ---
    tag_ids = list(instance.tags.values_list("id", flat=True)) if hasattr(instance, "tags") else []
    level_ids = list(instance.levels.values_list("id", flat=True)) if hasattr(instance, "levels") else []

    if not tag_ids and not level_ids:
        return  # nothing to match on

    user_ids = list(
        Profile.objects.filter(
            models.Q(tags__in=tag_ids) | models.Q(levels__in=level_ids)
        ).distinct().values_list("user_id", flat=True)
    )

    # optional: run in Celery batches for scale
    BATCH_SIZE = 500
    for i in range(0, len(user_ids), BATCH_SIZE):
        batch = user_ids[i : i + BATCH_SIZE]
        batch_invalidate_user_recommendations.delay(batch)