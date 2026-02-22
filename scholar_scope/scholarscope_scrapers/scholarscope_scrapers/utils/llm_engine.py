import os
import json
import asyncio
import trafilatura
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv
from pathlib import Path
# env_path = Path(__file__).resolve().parent.parent.parent / '.env'

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
        print(f"DEBUG: Loading .env from {env_path}")
        print(f"DEBUG: Key found? {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        
        
        self.model = genai.GenerativeModel(
             model_name="gemini-3-flash-preview", 
             generation_config={"response_mime_type": "application/json"}
         )

        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    def _prepare_content(self, input_data):
        if not input_data:
            return ""

        if isinstance(input_data, dict):
            return json.dumps(input_data, indent=2)

        if isinstance(input_data, str):
            if "<html" in input_data.lower() or "<body" in input_data.lower() or "<div" in input_data.lower():
                extracted = trafilatura.extract(input_data)
                return extracted if extracted else ""
            else:
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

        return await self._call_gemini(prompt)

    async def recover_specific_fields(self, html_content, missing_fields):
        clean_text = self._clean_html(html_content)
        
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

        return await self._call_gemini(prompt)

    async def _call_gemini(self, prompt, max_retries=3, initial_delay=2):
        delay = initial_delay

        for attempt in range(max_retries + 1):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    safety_settings=self.safety_settings
                )
                return json.loads(response.text)

            except Exception as e:
                error_msg = str(e)
                
                if "429" in error_msg or "ResourceExhausted" in error_msg:
                    if attempt < max_retries:
                        print(f"Gemini Rate Limit (Attempt {attempt+1}/{max_retries}). Sleeping {delay}s...")
                        await asyncio.sleep(delay)
                        
                        delay *= 2 
                        continue
                    else:
                        print(f"Gemini Rate Limit Persisted. Giving up after {max_retries} retries.")
                        return {}

                print(f"Gemini Error: {error_msg}")
                return {}
        
        return {}
    
    async def draft_essays(self, user_profile: dict, prompts_list: list[dict]) -> list[dict]:
        """
        Draft scholarship essay responses for a list of prompts using the user's profile.

        Args:
            user_profile: Rich dict of user data (name, bio, major, achievements, etc.)
            prompts_list: [{'id': 'scholarscope-ta-0', 'prompt': '...', 'max_words': 200}]

        Returns:
            [{'id': '...', 'draft': '...', 'word_count': int, 'confidence': str}]
        """
        if not prompts_list:
            return []

        # ── Build a rich profile context ──────────────────────────────────────
        profile_lines = [
            f"Name: {user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip(),
            f"Major / Field of Study: {user_profile.get('field_of_study', 'Not specified')}",
            f"University / Institution: {user_profile.get('institution', 'Not specified')}",
            f"Year of Study: {user_profile.get('year_of_study', 'Not specified')}",
            f"GPA: {user_profile.get('gpa', 'Not specified')}",
            f"Country / Nationality: {user_profile.get('country', 'Not specified')}",
            f"Bio & Background: {user_profile.get('bio') or 'Passionate student committed to academic excellence.'}",
            f"Key Achievements: {user_profile.get('achievements') or 'Not provided.'}",
            f"Career Goals: {user_profile.get('career_goals') or 'Not provided.'}",
            f"Extracurriculars / Volunteering: {user_profile.get('extracurriculars') or 'Not provided.'}",
            f"Financial Need Context: {user_profile.get('financial_need') or 'Not provided.'}",
        ]
        # Strip empty lines to avoid wasting tokens
        profile_context = "\n".join(line for line in profile_lines if not line.endswith("Not specified") or True)

        SYSTEM_PROMPT = (
            "You are an expert scholarship application coach who writes in the applicant's "
            "authentic voice — never generic, never fabricated. "
            "Rules you must follow:\n"
            "1. Use ONLY the information in the Student Profile; never invent facts, metrics, or jobs.\n"
            "2. Write in first person, as the student.\n"
            "3. Be specific and concrete — vague answers are automatically rejected.\n"
            "4. Respect the requested word limit exactly.\n"
            "5. End with a forward-looking sentence that ties back to the scholarship's purpose.\n"
            "6. Return ONLY the essay text — no preamble, no labels, no markdown."
        )

        # ── Run all drafts concurrently ───────────────────────────────────────
        import asyncio

        async def _draft_single(item: dict) -> dict:
            question   = item.get("prompt", "").strip()
            item_id    = item.get("id", "")
            max_words  = int(item.get("max_words") or 200)

            if not question:
                return {"id": item_id, "draft": "", "word_count": 0, "confidence": "low"}

            user_prompt = (
                f"Student Profile:\n{profile_context}\n\n"
                f"Scholarship Question:\n{question}\n\n"
                f"Write a response of NO MORE THAN {max_words} words."
            )

            try:
                response = await self.client.generate_content_async(
                    contents=user_prompt,
                    generation_config={
                        "temperature": 0.75,       # slight creativity, stays grounded
                        "max_output_tokens": max_words * 6,  # ~6 tokens/word buffer
                        "top_p": 0.9,
                    },
                    system_instruction=SYSTEM_PROMPT,
                )

                draft_text = response.text.strip()
                word_count = len(draft_text.split())

                # Confidence heuristic: penalise if profile was thin
                profile_filled = sum(
                    1 for k in ("bio", "achievements", "career_goals", "extracurriculars")
                    if user_profile.get(k)
                )
                confidence = "high" if profile_filled >= 3 else ("medium" if profile_filled >= 1 else "low")

                return {
                    "id":         item_id,
                    "draft":      draft_text,
                    "word_count": word_count,
                    "confidence": confidence,
                }

            except Exception as exc:
                self.logger.error(f"draft_essays: failed for prompt id={item_id}: {exc}")
                return {
                    "id":         item_id,
                    "draft":      "",
                    "word_count": 0,
                    "confidence": "failed",
                    "error":      str(exc),
                }

        results = await asyncio.gather(*[_draft_single(item) for item in prompts_list])
        return list(results)