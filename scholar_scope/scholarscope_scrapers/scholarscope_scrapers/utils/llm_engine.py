import os
import json
import asyncio
import trafilatura
import ollama
import google.generativeai as genai
from scholarships.models import ProfileChunk
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
import logging
from pathlib import Path
from scholarships.utils import generate_text
logger = logging.getLogger("scholar_scope")
logger.setLevel(logging.DEBUG)
# 2. Load it explicitly
def find_env_file():
    # Start at the current file's directory
    current_dir = Path(__file__).resolve().parent
    
    # Check current directory and move up 5 levels max
    for _ in range(5):
        env_path = current_dir / '.env'
        if env_path.exists():
            return env_path
        
        # Stop if we hit the root of the filesystem
        if current_dir.parent == current_dir:
            break
            
        current_dir = current_dir.parent
    
    return None
env_path = find_env_file()
load_dotenv(dotenv_path=env_path)

class LLMEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _prepare_content(self, input_data):
        """
        Clean HTML before sending to the LLM.

        Strips nav/sidebar/footer elements FIRST using parsel, THEN runs
        trafilatura. This prevents sidebar category lists like
        "undergraduate scholarships / phd scholarships / competitions"
        from polluting the LLM prompt as if they were eligibility criteria.
        """
        if not input_data:
            return ""
        if isinstance(input_data, dict):
            return json.dumps(input_data, indent=2)
        if isinstance(input_data, str):
            if any(tag in input_data.lower() for tag in ("<html", "<body", "<div")):
                try:
                    from parsel import Selector
                    sel = Selector(text=input_data)
                    noise_selectors = [
                        "nav", "header", "footer", "aside",
                        "[class*='sidebar']", "[class*='widget']",
                        "[class*='related']", "[class*='menu']",
                        "[class*='nav']", "[class*='breadcrumb']",
                        "[id*='sidebar']", "[id*='nav']", "[id*='menu']",
                    ]
                    for ns in noise_selectors:
                        try:
                            for el in sel.css(ns):
                                if el.root.getparent() is not None:
                                    el.root.getparent().remove(el.root)
                        except Exception:
                            pass
                    cleaned_html = sel.get()
                except Exception:
                    cleaned_html = input_data

                extracted = trafilatura.extract(
                    cleaned_html,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False,
                )
                return extracted if (extracted and len(extracted) > 100) else ""
            return input_data
        return str(input_data)
    
    
    async def extract_data(self, html_content, url):
        clean_text = self._prepare_content(html_content)
        if not clean_text or len(clean_text) < 100:
            return None

        prompt = f"""
        You are an expert data extraction agent. Analyze the text below and extract scholarship details into strictly valid JSON.

        SOURCE URL: {url}

        EXTRACTION RULES:
        1. **Dates:** Convert all deadlines to YYYY-MM-DD format. If only the month/year is given (e.g., "December 2025"), assume the last day of the month.
        2. **Nulls:** If a field is not found, return null. Do not invent data.
        3. **Lists:** Split requirements and eligibility into distinct, short bullet points.
        4. **Classification:** For 'tags' and 'levels', infer the best fit strictly from the allowed lists below.

        ALLOWED CLASSIFICATIONS:
        - Tags: ["international", "women", "stem", "merit", "need", "general"]
        - Levels: ["highschool", "undergraduate", "postgraduate", "phd"]

        REQUIRED JSON STRUCTURE:
        {{
            "is_valid": boolean (True if this describes a scholarship/grant, False if login page/blog/404),
            "title": "string (Exact official name)",
            "description": "string (2-3 sentence summary)",
            "reward": "string (e.g., '$5,000', 'Full Tuition', 'Varies')",
            "deadline": "YYYY-MM-DD or null",
            "start_date": "YYYY-MM-DD or null (Open date)",
            "requirements": ["list", "of", "strings"],
            "eligibility": ["list", "of", "strings"],
            "tags": ["tag1", "tag2"],
            "levels": ["level1", "level2"]
        }}

        TEXT TO PROCESS:
        {clean_text} 
        """
        return await generate_text(prompt, response_format="json")

    async def recover_specific_fields(self, html_content, missing_fields):
        clean_text = self._prepare_content(html_content)
        
        if not clean_text or len(clean_text) < 100:
            return {}

        field_schemas = {
            "title": '"title": "string"',
            "deadline": '"deadline": "YYYY-MM-DD" (or null)',
            "reward": '"reward": "string" (e.g. $5000)',
            "requirements": '"requirements": ["list", "of", "strings"]',
            "eligibility": '"eligibility": ["list", "of", "strings"]',
            "description": '"description": "string"',
        }
        
        requested_schema = ",\n".join(
            [field_schemas.get(field, f'"{field}": "string"') for field in missing_fields]
        )

        prompt = f"""
        Your job is to fill in MISSING data points from a partial extraction.
        
        CONTEXT:
        The user has already extracted some data but failed to find the following fields: {missing_fields}.
        
        INSTRUCTIONS:
        1. Search the text specifically for these missing fields.
        2. If a field is not explicitly stated, return null. Do NOT hallucinate.
        3. Format dates strictly as YYYY-MM-DD.
        4. Return ONLY a valid JSON object containing the requested fields.
        
        REQUIRED JSON SCHEMA:
        {{
            {requested_schema}
        }}

        TEXT TO PROCESS:
        {clean_text}
        """

        return await generate_text(prompt)    
    
    async def draft_essays(
        self,
        profile,
        prompts_list: list[dict],
        scholarship_context: str = "",   
    ) -> list[dict]:
        """
        Draft essays using RAG + structured profile facts.

        scholarship_context is the pre-built string from _build_scholarship_context_block()
        in views.py. It's appended between the structured profile facts and the question
        so the model sees exactly what the scholarship values without any special handling.

        Used by the local/async code path (development).
        The Celery production path builds the same string in views.py and passes it
        as part of `structured_context` to draft_single_essay.
        """
        from .rag import build_rag_context

        structured_context = (
            f"Name: {profile.full_name or 'Not provided'}\n"
            f"Field of Study: {profile.field_of_study or 'Not provided'}\n"
            f"Institution: {profile.institution or 'Not provided'}\n"
            f"Graduation Year: {profile.graduation_year or 'Not provided'}\n"
            f"Country: {profile.country or 'Not provided'}\n"
            f"GPA: {profile.gpa}/{profile.gpa_scale or 4.0}\n"
            f"Career Goals: {profile.career_goals or 'Not provided'}\n"
        )

        # Append inline scholarship context when present
        if scholarship_context and scholarship_context.strip():
            structured_context += scholarship_context

        SYSTEM_PROMPT = (
            "You are an expert scholarship application coach writing in the applicant's "
            "authentic voice. Rules:\n"
            "1. Use ONLY the provided profile information — never invent facts.\n"
            "2. Write in first person.\n"
            "3. Be specific and concrete — vague answers fail.\n"
            "4. Respect the word limit exactly.\n"
            "5. Return ONLY the essay text, no labels or markdown.\n"
            "6. If scholarship context is provided, tailor the essay to what "
            "   that scholarship values and who it targets."
        )

        semaphore = asyncio.Semaphore(2)

        async def _draft_single(item: dict) -> dict:
            async with semaphore:
                question  = item.get("prompt", "").strip()
                item_id   = item.get("id", "")
                max_words = int(item.get("max_words") or 200)

                if not question:
                    return {"id": item_id, "draft": "", "word_count": 0, "confidence": "low"}

                relevant_context = await build_rag_context(profile, question)

                user_prompt = (
                    f"Instructions:\n{SYSTEM_PROMPT}\n\n"
                    f"Structured Profile:\n{structured_context}\n\n"
                    f"Relevant Experience (retrieved for this question):\n{relevant_context}\n\n"
                    f"Scholarship Question:\n{question}\n\n"
                    f"Write a response of NO MORE THAN {max_words} words."
                )

                try:
                    if os.getenv("USE_OLLAMA") == "True":
                        response = await asyncio.to_thread(
                            ollama.generate,
                            model="gpt-oss:120b-cloud",
                            prompt=user_prompt,
                            options={"temperature": 0.75, "num_predict": max_words * 6},
                        )
                        draft_text = response["response"].strip()
                    else:
                        draft_text = await generate_text(user_prompt, response_format="text", max_words=max_words)

                    def _count_chunks(p):
                        return ProfileChunk.objects.filter(profile=p).exclude(text="").count()

                    filled_chunks = await sync_to_async(_count_chunks)(profile)
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
                    logger.error(f"[RAG] Draft failed for prompt {item_id}: {exc}")
                    return {"id": item_id, "draft": "", "word_count": 0, "confidence": "failed"}

        results = await asyncio.gather(*[_draft_single(item) for item in prompts_list])
        return list(results)

    async def refine_essay(
        self,
        profile_dict: dict,
        original_prompt: str,
        current_draft: str,
        instruction: str,
        max_words: int = 200,
    ) -> dict:
        """
        Refine an existing essay draft based on a user's specific instruction.
        Preserves factual accuracy while applying the stylistic/content change.
        """
        instructions = (
            "You are an expert scholarship application editor. "
            "You are given an existing draft and a specific refinement instruction from the student. "
            "Your job is to revise the draft according to the instruction while:\n"
            "1. Keeping all true facts from the original — never invent new ones.\n"
            "2. Maintaining first-person voice.\n"
            "3. Staying within the word limit.\n"
            "4. Applying the instruction precisely and specifically.\n"
            "5. Returning ONLY the revised essay text — no labels, no preamble."
        )

        name = f"{profile_dict.get('first_name', '')} {profile_dict.get('last_name', '')}".strip()

        user_prompt = (
            f"{instructions}"
            f"Student: {name or 'Not provided'}\n"
            f"Field of Study: {profile_dict.get('field_of_study', 'Not provided')}\n\n"
            f"Original Scholarship Question:\n{original_prompt}\n\n"
            f"Current Draft:\n{current_draft}\n\n"
            f"Student's Refinement Instruction:\n{instruction}\n\n"
            f"Rewrite the draft applying the instruction above. "
            f"Maximum {max_words} words. Return only the revised text."
        )

        try:
            response = await generate_text(prompt=user_prompt, max_words=max_words)

            revised = response.text.strip()
            return {
                "draft":      revised,
                "word_count": len(revised.split()),
                "confidence": "high",  
            }

        except Exception as exc:
            logger.error(f"[LLM] refine_essay failed: {exc}")
            raise
