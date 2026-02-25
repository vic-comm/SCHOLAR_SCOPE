import os
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Fixed — configure once at module level, reuse model
import google.generativeai as genai
import os

_gemini_model = None

def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        _gemini_model = genai.GenerativeModel(model_name="gemini-2.0-flash")
    return _gemini_model

@shared_task(
    bind=True,
    name="scholarships.draft_single_essay",
    max_retries=3,
    default_retry_delay=10,
    rate_limit="20/m",          # Global: max 20 Gemini calls/minute across ALL workers
    queue="llm",                # Dedicated queue — separate from embedding tasks
    acks_late=True,             # Only ack after completion, not on receipt
    reject_on_worker_lost=True, # Re-queue if worker dies mid-task
)
def draft_single_essay(
    self,
    profile_id: int,
    prompt_item: dict,          # {"id": "...", "prompt": "...", "max_words": 200}
    structured_context: str,    # Pre-built from profile fields
) -> dict:
    """
    Draft a single essay. Rate-limited globally via Celery rate_limit.
    Runs in a sync Celery worker — no asyncio needed here.
    
    Returns: {"id": ..., "draft": ..., "word_count": ..., "confidence": ...}
    """
    from scholarships.models import ProfileChunk
    from scholarscope_scrapers.scholarscope_scrapers.utils.rag import retrieve_relevant_chunks_sync

    question  = prompt_item.get("prompt", "").strip()
    item_id   = prompt_item.get("id", "")
    max_words = int(prompt_item.get("max_words") or 200)

    if not question:
        return {"id": item_id, "draft": "", "word_count": 0, "confidence": "low"}

    try:
        # ── RAG retrieval (sync — no asyncio in Celery tasks) ─────────────
        from scholarships.models import Profile
        profile = Profile.objects.select_related("user").get(id=profile_id)
        chunks  = retrieve_relevant_chunks_sync(profile, question)

        relevant_context = "\n\n".join(
            f"[{c['chunk_type'].replace('_', ' ').title()}]\n{c['text']}"
            for c in chunks
        ) or "No relevant profile information available."

        # ── Build prompt ──────────────────────────────────────────────────
        SYSTEM_PROMPT = (
            "You are an expert scholarship application coach writing in the applicant's "
            "authentic voice. Rules:\n"
            "1. Use ONLY the provided profile information — never invent facts.\n"
            "2. Write in first person.\n"
            "3. Be specific and concrete — vague answers fail.\n"
            "4. Respect the word limit exactly.\n"
            "5. Return ONLY the essay text, no labels or markdown."
        )

        user_prompt = (
            f"intructions: {SYSTEM_PROMPT}"
            f"Structured Profile:\n{structured_context}\n\n"
            f"Relevant Experience (retrieved for this question):\n{relevant_context}\n\n"
            f"Scholarship Question:\n{question}\n\n"
            f"Write a response of NO MORE THAN {max_words} words."
        )

        # ── Gemini call (sync in Celery worker) ───────────────────────────
        model = _get_gemini_model()
        response = model.generate_content(
            contents=user_prompt,
            generation_config={
                "temperature": 0.75,
                "max_output_tokens": max_words * 6,
                "top_p": 0.9,
            }
        )

        draft_text = response.text.strip()

        # ── Confidence based on how many chunks the user filled ───────────
        filled_chunks = ProfileChunk.objects.filter(
            profile=profile
        ).exclude(text="").count()

        confidence = (
            "high"   if filled_chunks >= 5 else
            "medium" if filled_chunks >= 2 else
            "low"
        )

        return {
            "id":         item_id,
            "draft":      draft_text,
            "word_count": len(draft_text.split()),
            "confidence": confidence,
        }

    except Exception as exc:
        error_msg = str(exc)

        # Rate limit from Google — retry with exponential backoff
        if "429" in error_msg or "ResourceExhausted" in error_msg:
            raise self.retry(
                exc=exc,
                countdown=2 ** self.request.retries * 15,  # 15s, 30s, 60s
            )

        logger.exception(f"[Essay Task] Failed for prompt {item_id}: {exc}")
        return {"id": item_id, "draft": "", "word_count": 0, "confidence": "failed"}

# tasks/llm_tasks.py (continued)

@shared_task(
    name="scholarships.draft_essays_batch",
    queue="llm",
)
def draft_essays_batch(
    job_id: str,
    profile_id: int,
    prompts_list: list[dict],
    structured_context: str,
) -> None:
    """
    Fan-out coordinator: dispatches one draft_single_essay task per prompt,
    then collects results into Redis when all are done.
    
    Uses Celery chord: parallel tasks → callback when all complete.
    """
    from celery import chord
    # Build the parallel group
    essay_tasks = [
        draft_single_essay.s(
            profile_id=profile_id,
            prompt_item=item,
            structured_context=structured_context,
        )
        for item in prompts_list
    ]

    # chord: run all in parallel, then call collect when ALL finish
    chord(essay_tasks)(collect_essay_results.s(job_id=job_id))


@shared_task(name="scholarships.collect_essay_results")
def collect_essay_results(results: list[dict], job_id: str) -> None:
    """
    Chord callback: receives all essay results, stores in Redis.
    The polling endpoint reads from here.
    """
    from django.core.cache import cache

    successful = [r for r in results if r.get("confidence") != "failed"]
    failed_ids = [r["id"] for r in results if r.get("confidence") == "failed"]

    cache.set(
        f"essay_job:{job_id}",
        {
            "status":  "complete",
            "drafts":  successful,
            "failed":  failed_ids,
            "count":   len(successful),
        },
        timeout=3600,  
    )

    logger.info(f"[Essay Job] {job_id} complete: {len(successful)} drafts, {len(failed_ids)} failed.")

