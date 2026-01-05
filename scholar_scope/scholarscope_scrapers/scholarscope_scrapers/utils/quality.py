import re

class QualityCheck:
    GARBAGE_PHRASES = {
        "general": {
            "apply", "apply now", "click here", "read more", "submit",
            "skip to content", "menu", "search", "loading...", "tba", "none"
        },
        "title": {
            "home", "scholarships", "search results", "all scholarships", 
            "welcome", "index", "page 1", "unknown"
        },
        "reward": {
            "varies", "see details", "check website", "n/a", "unknown", 
            "amount", "award"
        }
    }

    @classmethod
    def check(cls, field_name: str, value) -> bool:
        """
        Returns False if the value is Garbage/Null. 
        Returns True if the value looks valid.
        """
        if not value:
            return False

        if field_name == "title":
            return cls._is_valid_title(str(value))
        elif field_name in ["reward", "amount"]:
            return cls._is_valid_reward(str(value))
        elif field_name in ["end_date", "start_date", "deadline"]:
            return cls._is_valid_date_string(str(value))
        elif field_name in ["requirements", "eligibility", "tags"]:
            return cls._is_valid_list(value)
        elif field_name == "description":
            return cls._is_valid_description(str(value))
        
        return not cls._is_generic_garbage(str(value))

    
    @classmethod
    def _is_generic_garbage(cls, text: str) -> bool:
        t = text.strip().lower()
        if len(t) < 3: return True
        if t in cls.GARBAGE_PHRASES["general"]: return True
        # Check density: "---" or "..." is garbage
        if sum(c.isalnum() for c in t) / len(t) < 0.5: return True
        return False

    @classmethod
    def _is_valid_title(cls, text: str) -> bool:
        t = text.strip().lower()
        if cls._is_generic_garbage(text): return False
        
        if t in cls.GARBAGE_PHRASES["title"]: return False
        
        # A good title is usually 10-100 chars
        if len(t) < 5 or len(t) > 200: return False
        
        return True

    @classmethod
    def _is_valid_reward(cls, text: str) -> bool:
        t = text.strip().lower()
        if cls._is_generic_garbage(text): return False
        if t in cls.GARBAGE_PHRASES["reward"]: return False

        if not any(c.isdigit() for c in t) and "tuition" not in t and "funded" not in t:
            return False
            
        return True

    @classmethod
    def _is_valid_date_string(cls, text: str) -> bool:
        t = text.strip().lower()
        if cls._is_generic_garbage(text): return False
        
        # Scraper often grabs label "Deadline:" instead of date
        if t.endswith(":"): return False
        
        # Must have at least one digit (for day/year)
        if not any(c.isdigit() for c in t): 
            return False
            
        return True

    @classmethod
    def _is_valid_description(cls, text: str) -> bool:
        if len(text) < 50: return False
        if "cookie" in text.lower(): return False
        return True

    @classmethod
    def _is_valid_list(cls, items: list) -> bool:
        if not items: return False
        if items == ["Requirements not specified"]: return False
        
        valid_count = 0
        for item in items:
            if not cls._is_generic_garbage(item):
                valid_count += 1
        
        # If list is ["Click here", "Apply"], valid_count is 0 -> Invalid
        return valid_count > 0