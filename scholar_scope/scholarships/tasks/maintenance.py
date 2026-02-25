from celery import shared_task
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task
def outdated_scholarships():
    from scholarships.models import Scholarship
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now().date() - timedelta(days=30)
    updated = Scholarship.objects.filter(
        end_date__lte=cutoff,
        active=True,  # don't re-update already inactive ones
    ).update(active=False)
    
    logger.info(f"[Tasks] Marked {updated} scholarships as inactive.")
    return updated

@shared_task
def batch_invalidate_user_recommendations(user_ids):
    from django.core.cache import cache
    from scholarships.utils import _rec_cache_key
    for uid in user_ids:
        cache.delete(_rec_cache_key(uid))

@shared_task
def remove_semantic_duplicates(threshold=0.95):
    from scholarships.models import Scholarship
    print("Starting Semantic Deduplication...")
    scholarships = list(Scholarship.objects.filter(
        active=True, 
        embedding__isnull=False
    ).values('id', 'title', 'embedding', 'description'))
    
    if len(scholarships) < 2:
        return "Not enough items to check."


    embeddings = np.array([s['embedding'] for s in scholarships])
    ids = [s['id'] for s in scholarships]
    
    similarity_matrix = cosine_similarity(embeddings)
    
    upper_triangle = np.triu(similarity_matrix, k=1)
    
    duplicate_indices = np.where(upper_triangle > threshold)
    
    deleted_count = 0
    deleted_ids = set()

    # Zip turns the two arrays into pairs of (i, j)
    for i, j in zip(*duplicate_indices):
        id_a = ids[i]
        id_b = ids[j]
        
        # Skip if we already deleted one of them
        if id_a in deleted_ids or id_b in deleted_ids:
            continue
            
        item_a = scholarships[i]
        item_b = scholarships[j]
        
        print(f"MATCH FOUND ({upper_triangle[i][j]:.3f}):")
        print(f"   A: {item_a['title']}")
        print(f"   B: {item_b['title']}")
        
        
        len_a = len(item_a['description'] or "")
        len_b = len(item_b['description'] or "")
        
        id_to_delete = id_b if len_a >= len_b else id_a
        
        Scholarship.objects.filter(id=id_to_delete).delete()
        deleted_ids.add(id_to_delete)
        deleted_count += 1
    return f"Cleanup Complete. Removed {deleted_count} semantic duplicates."
