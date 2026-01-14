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
    def _clean_html(self, html_content):
        return trafilatura.extract(html_content) or ""

    async def extract_data(self, html_content, url):
        clean_text = self._clean_html(html_content)
        
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
                # Run sync Gemini call in a thread
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    safety_settings=self.safety_settings
                )
                return json.loads(response.text)

            except Exception as e:
                error_msg = str(e)
                
                # Check for Rate Limit (429) or Overloaded (503)
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