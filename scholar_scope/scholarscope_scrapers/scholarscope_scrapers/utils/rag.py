import logging
from pgvector.django import CosineDistance
from scholarships.models import ProfileChunk
from asgiref.sync import sync_to_async
from scholarships.utils import get_text_embedding

logger = logging.getLogger(__name__)

TOP_K_CHUNKS = 3

def retrieve_relevant_chunks(profile, query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
    """
    Given a natural language query (the essay prompt), return the
    top-k most semantically relevant profile chunks.

    Returns a list of dicts: [{"chunk_type": ..., "text": ...}]
    """
    query_embedding = get_text_embedding(query)
    if query_embedding is None:
        # Fallback: return all non-empty chunks
        return _all_chunks(profile)

    chunks = (
        ProfileChunk.objects.filter(profile=profile)
        .exclude(embedding__isnull=True)
        .order_by(CosineDistance("embedding", query_embedding))
        [:top_k]
    )

    results = [{"chunk_type": c.chunk_type, "text": c.text} for c in chunks]

    if not results:
        logger.warning(f"[RAG] No chunks found for profile {profile.id} — using fallback.")
        return _all_chunks(profile)

    return results


def _all_chunks(profile) -> list[dict]:
    """Fallback when embeddings aren't ready yet."""
    return [
        {"chunk_type": c.chunk_type, "text": c.text}
        for c in ProfileChunk.objects.filter(profile=profile)
        if c.text.strip()
    ]


async def build_rag_context(profile, query: str) -> str:
    """
    Build the context string that gets injected into the LLM prompt.
    Only includes chunks that are semantically relevant to the query.
    """
    chunks = await sync_to_async(retrieve_relevant_chunks)(profile, query)
    if not chunks:
        return "No relevant profile information available."

    lines = []
    for chunk in chunks:
        label = chunk["chunk_type"].replace("_", " ").title()
        lines.append(f"[{label}]\n{chunk['text']}")

    return "\n\n".join(lines)

def retrieve_relevant_chunks_sync(profile, query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
    """
    Synchronous version for use in Celery tasks.
    Identical logic to retrieve_relevant_chunks but no async wrapper needed.
    """
    query_embedding = get_text_embedding(query)
    if query_embedding is None:
        return _all_chunks(profile)

    chunks = (
        ProfileChunk.objects.filter(profile=profile)
        .exclude(embedding__isnull=True)
        .order_by(CosineDistance("embedding", query_embedding))
        [:top_k]
    )

    results = [{"chunk_type": c.chunk_type, "text": c.text} for c in chunks]
    return results if results else _all_chunks(profile)
