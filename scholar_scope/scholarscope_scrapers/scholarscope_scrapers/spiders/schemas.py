from datetime import datetime, date
from typing import List, Optional, Set
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

# Constants remain the same
ALLOWED_LEVELS = {
    "highschool", "undergraduate", "postgraduate", "phd", "other", "unspecified"
}

ALLOWED_TAGS = {
    "international", "women", "stem", "merit", "need", "general"
}

class ScholarshipScrapedSchema(BaseModel):
    title: str = Field(..., min_length=5)
    link: HttpUrl  # Changed from AnyHttpUrl to HttpUrl (Standard in V2)
    scraped_at: datetime

    description: Optional[str] = None
    reward: Optional[str] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    requirements: List[str] = Field(default_factory=list)
    eligibility: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    levels: List[str] = Field(default_factory=list)
    fingerprint: Optional[str] = None

    # --- FIELD VALIDATORS (Formerly @validator) ---

    @field_validator("title", "description", "reward", mode="before")
    @classmethod
    def normalize_text(cls, v):
        """Fixes non-breaking spaces and cleans whitespace."""
        if not v:
            return None
        return " ".join(str(v).replace("\xa0", " ").split())

    @field_validator("requirements", "eligibility", mode="before")
    @classmethod
    def clean_lists(cls, v):
        """Cleans bullet points and dedupes lists."""
        if not v:
            return []

        cleaned = []
        NOISE = {
            "requirements", "eligibility", "criteria", "documents", 
            "see below", "n/a", ":", "none", "click here"
        }

        for item in v:
            if not isinstance(item, str):
                continue
            
            text = item.strip()
            
            if len(text) < 5 or len(text) > 300:
                continue
            
            # Remove bullets explicitly
            text = text.lstrip("-•*").strip()

            if text.lower().rstrip(":") in NOISE:
                continue
                
            cleaned.append(text.capitalize())

        # Deduplicate while preserving order
        return list(dict.fromkeys(cleaned))

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        if not v:
            return ["general"]
        # Filter: Only allow tags that exist in our system
        # Ensure v is iterable
        if isinstance(v, str):
            v = [v]
        tags = {t.lower().strip() for t in v if t}
        valid = tags & ALLOWED_TAGS
        return list(valid) or ["general"]

    @field_validator("levels", mode="before")
    @classmethod
    def normalize_levels(cls, v):
        if not v:
            return ["unspecified"]
        if isinstance(v, str):
            v = [v]
        levels = {l.lower().strip() for l in v if l}
        valid = levels & ALLOWED_LEVELS
        return list(valid) or ["unspecified"]

    @field_validator("end_date")
    @classmethod
    def validate_deadline(cls, v):
        if v and v.year < 2000:
            return None 
        return v

    # --- MODEL VALIDATORS (Formerly @root_validator) ---

    @model_validator(mode='after')
    def check_date_consistency(self):
        """
        Ensures start_date is not after end_date.
        In V2, 'self' is the model instance, not a dict.
        """
        if self.start_date and self.end_date and self.start_date > self.end_date:
            # Intelligent Swap using python tuple unpacking
            self.start_date, self.end_date = self.end_date, self.start_date
            
        return self