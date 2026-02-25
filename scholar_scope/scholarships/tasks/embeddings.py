from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def embed_profile_chunks(self, profile_id: int) -> None:
    from scholarships.models import Profile, ProfileChunk
    from scholarships.utils import get_text_embedding

    CHUNK_FIELD_MAP = {
        "leadership":      "leadership_experience",
        "academic":        "academic_achievements",
        "financial_need":  "financial_need_statement",
        "career_goals":    "career_goals",
        "community_impact":"community_impact",
        "challenges":      "challenges_overcome",
        "research":        "research_experience",
        "extracurriculars":"extracurriculars",
        "bio":             "bio",
    }

    try:
        profile = Profile.objects.get(id=profile_id)

        for chunk_type, field_name in CHUNK_FIELD_MAP.items():
            text = (getattr(profile, field_name, "") or "").strip()
            if not text:
                # Delete stale chunk if user cleared the field
                ProfileChunk.objects.filter(
                    profile=profile, chunk_type=chunk_type
                ).delete()
                continue

            embedding = get_text_embedding(text)
            if embedding is None:
                continue

            ProfileChunk.objects.update_or_create(
                profile=profile,
                chunk_type=chunk_type,
                defaults={"text": text, "embedding": embedding},
            )

    except Profile.DoesNotExist:
        return
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task
def generate_scholarship_embedding(scholarship_id):
    from scholarships.models import Scholarship
    from scholarships.utils import get_text_embedding
    
    s = Scholarship.objects.get(id=scholarship_id)
    text = f"{s.title}. {s.description}. {s.eligibility or ''}. {s.requirements or ''}"
    vector = get_text_embedding(text)
    if vector:
        Scholarship.objects.filter(id=scholarship_id).update(embedding=vector)

@shared_task
def generate_profile_embedding(profile_id):
    from scholarships.models import Profile
    from scholarships.utils import get_text_embedding
    from django.core.cache import cache
    
    profile = Profile.objects.get(id=profile_id)
    text = f"{profile.field_of_study}. {profile.bio}. {profile.preferred_scholarship_types}. {profile.preferred_countries}"
    vector = get_text_embedding(text)
    if vector:
        Profile.objects.filter(id=profile_id).update(embedding=vector)
    
@shared_task
def batch_invalidate_user_recommendations(user_ids):
    from django.core.cache import cache
    from scholarships.utils import _rec_cache_key
    for uid in user_ids:
        cache.delete(_rec_cache_key(uid))
