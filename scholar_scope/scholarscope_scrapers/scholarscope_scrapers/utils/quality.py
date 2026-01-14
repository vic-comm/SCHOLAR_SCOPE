import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

class QualityCheck:
    GARBAGE_PHRASES = {
        "general": {
            "apply", "apply now", "click here", "read more", "submit",
            "skip to content", "menu", "search", "loading", "tba", "none",
            "more info", "learn more", "details", "sign up", "register",
            "log in", "login", "home page", "back to top", "continue reading",
            "share", "tweet", "facebook", "print", "email", "download"
        },
        "title": {
            "home", "scholarships", "search results", "all scholarships", 
            "welcome", "index", "page 1", "unknown", "untitled", "scholarship",
            "scholarship opportunity", "opportunity", "financial aid",
            "scholarship search", "find scholarships", "browse scholarships"
        },
        "reward": {
            "varies", "see details", "check website", "n/a", "unknown", 
            "amount", "award", "value", "prize", "up to", "contact us",
            "call for amount", "refer to website", "scholarship amount",
            "view details", "tbd", "to be determined"
        },
        "description": {
            "we use cookies", "this website uses", "accept cookies",
            "javascript required", "please enable javascript", "error 404",
            "page not found", "access denied", "privacy policy", "terms of service"
        },
        "navigation": {
        "scholarships by level", "scholarships by country", "search for:", 
        "recent posts", "categories", "archives", "meta", "links",
        "home", "about", "contact", "privacy policy"}
    }
    
    # Keywords that should appear in legitimate scholarship content
    SCHOLARSHIP_KEYWORDS = {
        "student", "education", "university", "college", "academic",
        "undergraduate", "graduate", "tuition", "study", "degree",
        "applicant", "enrollment", "gpa", "merit", "financial", "award",
        "eligible", "scholarship", "grant", "application"
    }

    @classmethod
    def check(cls, field_name: str, value: Any) -> Dict[str, Any]:
        """
        Returns a dict with:
        - 'valid': bool (True if value looks valid)
        - 'confidence': float (0.0-1.0, confidence in the validation)
        - 'reason': str (why it failed, if applicable)
        - 'severity': str ('critical'|'warning'|'minor')
        """
        if not value:
            return {
                'valid': False,
                'confidence': 1.0,
                'reason': 'Empty or None value',
                'severity': 'critical'
            }

        validators = {
            "title": cls._is_valid_title,
            "reward": cls._is_valid_reward,
            "amount": cls._is_valid_reward,
            "end_date": cls._is_valid_date_string,
            "start_date": cls._is_valid_date_string,
            "deadline": cls._is_valid_date_string,
            "requirements": cls._is_valid_list,
            "eligibility": cls._is_valid_list,
            "tags": cls._is_valid_list,
            "description": cls._is_valid_description,
            "url": cls._is_valid_url,
        }
        
        validator = validators.get(field_name, cls._is_generic_valid)
        return validator(value)

    @classmethod
    def _is_generic_garbage(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text is generic garbage.
        Returns (is_garbage, reason)
        """
        t = text.strip().lower()
        
        # Too short
        if len(t) < 3:
            return True, "Too short (< 3 chars)"
        
        # Exact match to garbage phrases
        if t in cls.GARBAGE_PHRASES["general"]:
            return True, f"Matches garbage phrase: '{t}'"
        
        # Check alphanumeric density
        alnum_chars = sum(c.isalnum() for c in t)
        if alnum_chars == 0:
            return True, "No alphanumeric characters"
        
        if len(t) > 0 and alnum_chars / len(t) < 0.4:
            return True, f"Low alphanumeric density ({alnum_chars}/{len(t)})"
        
        # Repeated characters (e.g., "......." or "-------")
        if re.search(r'(.)\1{5,}', t):
            return True, "Contains repeated characters"
        
        # Just a year or short number
        if t.isdigit() and len(t) <= 4:
            return True, "Just a number"
        
        # Common navigation patterns
        nav_patterns = [
            r'^page \d+$',
            r'^\d+ of \d+$',
            r'^next$',
            r'^previous$',
            r'^prev$',
        ]
        for pattern in nav_patterns:
            if re.match(pattern, t):
                return True, f"Navigation element: '{t}'"
            
        return False, None

    @classmethod
    def _is_valid_title(cls, text: str) -> Dict[str, Any]:
        t = text.strip()
        t_lower = t.lower()
        
        # Check for garbage
        is_garbage, garbage_reason = cls._is_generic_garbage(text)
        if is_garbage:
            return {
                'valid': False,
                'confidence': 0.95,
                'reason': garbage_reason,
                'severity': 'critical'
            }
        
        # Exact match to title garbage phrases
        if t_lower in cls.GARBAGE_PHRASES["title"]:
            return {
                'valid': False,
                'confidence': 0.9,
                'reason': f"Generic title phrase: '{t_lower}'",
                'severity': 'critical'
            }
        
        # Title length checks
        if len(t) < 10:
            return {
                'valid': False,
                'confidence': 0.85,
                'reason': f'Too short ({len(t)} chars, minimum 10)',
                'severity': 'critical'
            }
        
        if len(t) > 250:
            return {
                'valid': False,
                'confidence': 0.75,
                'reason': f'Too long ({len(t)} chars, maximum 250)',
                'severity': 'warning'
            }
        
        # All uppercase titles (likely headers/nav)
        if t.isupper() and len(t) > 20:
            return {
                'valid': False,
                'confidence': 0.8,
                'reason': 'All uppercase (likely navigation/header)',
                'severity': 'warning'
            }
        
        # Check for URLs in title
        if t_lower.startswith(('http://', 'https://', 'www.')) or re.search(r'\.(com|org|edu|gov|net)(/|$)', t_lower):
            return {
                'valid': False,
                'confidence': 0.9,
                'reason': 'Contains URL',
                'severity': 'critical'
            }
        
        # Word count check
        words = [w for w in t.split() if len(w) > 0]
        if len(words) < 2:
            return {
                'valid': False,
                'confidence': 0.85,
                'reason': 'Only one word',
                'severity': 'warning'
            }
        
        # Calculate confidence based on scholarship keyword presence
        keyword_matches = sum(1 for keyword in cls.SCHOLARSHIP_KEYWORDS if keyword in t_lower)
        
        if keyword_matches >= 2:
            confidence = 0.9
        elif keyword_matches == 1:
            confidence = 0.75
        else:
            confidence = 0.6
        
        # Boost confidence for reasonable length and structure
        if 15 <= len(t) <= 150 and len(words) >= 3:
            confidence = min(confidence + 0.1, 0.95)
        
        return {
            'valid': True,
            'confidence': confidence,
            'reason': None,
            'severity': None
        }

    @classmethod
    def _is_valid_reward(cls, text: str) -> Dict[str, Any]:
        t = text.strip()
        t_lower = t.lower()
        
        # Check for garbage
        is_garbage, garbage_reason = cls._is_generic_garbage(text)
        if is_garbage:
            return {
                'valid': False,
                'confidence': 0.95,
                'reason': garbage_reason,
                'severity': 'critical'
            }
        
        # Check against reward garbage phrases
        if t_lower in cls.GARBAGE_PHRASES["reward"]:
            return {
                'valid': False,
                'confidence': 0.9,
                'reason': f"Vague reward phrase: '{t_lower}'",
                'severity': 'critical'
            }
        
        # Must contain either a number or specific funding keywords
        has_digit = any(c.isdigit() for c in t)
        funding_keywords = ['tuition', 'funded', 'full ride', 'scholarship', 'stipend', 'allowance']
        has_funding_keyword = any(kw in t_lower for kw in funding_keywords)
        
        if not has_digit and not has_funding_keyword:
            return {
                'valid': False,
                'confidence': 0.9,
                'reason': 'No amount or funding keyword',
                'severity': 'critical'
            }
        
        # Calculate confidence based on specificity
        confidence = 0.5
        
        # High confidence indicators
        if re.search(r'[\$£€¥₹]\s*[\d,]+', t):  # Currency symbol with amount
            confidence = 0.95
        elif re.search(r'\d+[,.]?\d*\s*(dollars?|usd|euro|euros?|pounds?|gbp)', t_lower):
            confidence = 0.9
        elif re.search(r'\d+k', t_lower):  # e.g., "10k scholarship"
            confidence = 0.85
        elif 'full tuition' in t_lower or 'full ride' in t_lower or 'fully funded' in t_lower:
            confidence = 0.9
        elif has_digit and any(kw in t_lower for kw in ['per year', 'annually', 'total']):
            confidence = 0.8
        elif has_digit:
            confidence = 0.7
        elif has_funding_keyword:
            confidence = 0.6
        
        # Penalty for vague qualifiers
        vague_qualifiers = ['up to', 'varies', 'various', 'multiple', 'range']
        if any(vq in t_lower for vq in vague_qualifiers):
            confidence *= 0.8
        
        return {
            'valid': True,
            'confidence': confidence,
            'reason': None,
            'severity': None
        }

    @classmethod
    def _is_valid_date_string(cls, text: str) -> Dict[str, Any]:
        t = text.strip()
        t_lower = t.lower()
        
        # Check for garbage
        is_garbage, garbage_reason = cls._is_generic_garbage(text)
        if is_garbage:
            return {
                'valid': False,
                'confidence': 0.95,
                'reason': garbage_reason,
                'severity': 'critical'
            }
        
        # Ends with colon (likely a label)
        if t.endswith(':'):
            return {
                'valid': False,
                'confidence': 0.95,
                'reason': "Ends with colon (likely a label)",
                'severity': 'critical'
            }
        
        # Must contain at least one digit
        if not any(c.isdigit() for c in t):
            return {
                'valid': False,
                'confidence': 0.95,
                'reason': 'No digits found',
                'severity': 'critical'
            }
        
        # Too short to be a valid date
        if len(t) < 5:
            return {
                'valid': False,
                'confidence': 0.85,
                'reason': f'Too short ({len(t)} chars)',
                'severity': 'warning'
            }
        
        confidence = 0.5
        
        # Check for specific date patterns (high confidence)
        date_patterns = [
            (r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', 0.95),  # 12/31/2024
            (r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', 0.95),     # 2024-12-31
            (r'\b\d{1,2}\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b', 0.95),  # 15 January 2024
            (r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b', 0.95),  # January 15, 2024
            (r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+\d{1,2},?\s+\d{4}\b', 0.9),  # Jan 15, 2024
            (r'\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s+\d{4}\b', 0.9),  # 15 Jan 2024
        ]
        
        for pattern, pattern_confidence in date_patterns:
            if re.search(pattern, t_lower):
                confidence = pattern_confidence
                break
        
        # Month names boost confidence
        month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                      'july', 'august', 'september', 'october', 'november', 'december']
        month_abbrevs = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec']
        
        if any(month in t_lower for month in month_names):
            confidence = max(confidence, 0.85)
        elif any(abbrev in t_lower for abbrev in month_abbrevs):
            confidence = max(confidence, 0.8)
        
        # Valid relative/rolling dates
        relative_dates = ['ongoing', 'rolling', 'rolling deadline', 'varies', 'annual', 'annually', 
                         'quarterly', 'open', 'continuous']
        if any(rd in t_lower for rd in relative_dates):
            confidence = 0.8
        
        # Year present (4 digits)
        if re.search(r'\b(19|20)\d{2}\b', t):
            confidence = max(confidence, 0.75)
        
        return {
            'valid': True,
            'confidence': confidence,
            'reason': None,
            'severity': None
        }

    @classmethod
    def _is_valid_description(cls, text: str) -> Dict[str, Any]:
        t = text.strip()
        t_lower = t.lower()
        
        # Minimum length requirement
        if len(t) < 100:
            return {
                'valid': False,
                'confidence': 0.9,
                'reason': f'Too short ({len(t)} chars, minimum 100)',
                'severity': 'critical'
            }
        
        # Check for error/cookie messages
        for phrase in cls.GARBAGE_PHRASES["description"]:
            if phrase in t_lower:
                return {
                    'valid': False,
                    'confidence': 0.95,
                    'reason': f"Contains error/cookie text: '{phrase}'",
                    'severity': 'critical'
                }
        
        mashup_indicators = [
            " | how to apply", 
            " | fully funded", 
            "scholarship region",
            "read also:",
            "related posts:",
            "you may also like"
        ]

        indicator_count = sum(1 for ind in mashup_indicators if ind in t_lower)
        if indicator_count >= 2:
             return {
                'valid': False,
                'confidence': 0.8,
                'reason': 'Description appears to be a mashup of Related Posts',
                'severity': 'critical'
            }
        sentences = [s.strip() for s in re.split(r'[.!?]+', t) if len(s.strip()) > 15]
        if len(sentences) < 2:
            return {
                'valid': False,
                'confidence': 0.75,
                'reason': 'Only one sentence',
                'severity': 'warning'
            }
        
        # Word count
        word_count = len(t.split())
        if word_count < 30:
            return {
                'valid': False,
                'confidence': 0.8,
                'reason': f'Too few words ({word_count}, minimum 30)',
                'severity': 'warning'
            }
        
        # Calculate confidence based on scholarship keyword density
        keyword_matches = sum(1 for kw in cls.SCHOLARSHIP_KEYWORDS if kw in t_lower)
        keyword_density = keyword_matches / max(word_count / 100, 1)  # keywords per 100 words
        
        # Base confidence
        if keyword_density >= 3:
            confidence = 0.95
        elif keyword_density >= 2:
            confidence = 0.85
        elif keyword_density >= 1:
            confidence = 0.75
        else:
            confidence = 0.6
        
        # Boost for good length
        if 150 <= len(t) <= 2000 and len(sentences) >= 3:
            confidence = min(confidence + 0.05, 0.95)
        
        # Penalty for very long descriptions (might be entire page content)
        if len(t) > 3000:
            confidence *= 0.9
        
        return {
            'valid': True,
            'confidence': confidence,
            'reason': None,
            'severity': None
        }

    @classmethod
    def _is_valid_list(cls, items) -> Dict[str, Any]:
        if not items:
            return {
                'valid': False,
                'confidence': 1.0,
                'reason': 'Empty list',
                'severity': 'critical'
            }
        
        if not isinstance(items, (list, tuple)):
            return {
                'valid': False,
                'confidence': 1.0,
                'reason': 'Not a list/tuple',
                'severity': 'critical'
            }
        
        # Check for placeholder lists
        placeholder_patterns = [
            ["requirements not specified"],
            ["not specified"],
            ["n/a"],
            ["none"],
            ["tbd"],
            ["to be determined"],
            ["see website"],
            ["check website"]
        ]
        
        items_lower = [str(item).lower().strip() for item in items]
        for pattern in placeholder_patterns:
            if items_lower == pattern:
                return {
                    'valid': False,
                    'confidence': 0.95,
                    'reason': f"Placeholder list: {items}",
                    'severity': 'critical'
                }
        
        # Count valid items
        valid_items = []
        garbage_items = []
        
        for item in items:
            is_garbage, reason = cls._is_generic_garbage(str(item))
            if not is_garbage:
                valid_items.append(item)
            else:
                garbage_items.append((item, reason))
        
        if not valid_items:
            return {
                'valid': False,
                'confidence': 0.95,
                'reason': f'All {len(items)} items are garbage',
                'severity': 'critical'
            }
        
        # Calculate confidence
        valid_ratio = len(valid_items) / len(items)
        
        # Base confidence on ratio
        if valid_ratio >= 0.9:
            confidence = 0.9
        elif valid_ratio >= 0.7:
            confidence = 0.8
        elif valid_ratio >= 0.5:
            confidence = 0.7
        else:
            confidence = 0.6
        
        # Check average item quality (substantiveness)
        avg_word_count = sum(len(str(item).split()) for item in valid_items) / len(valid_items)
        
        if avg_word_count >= 5:
            confidence = min(confidence + 0.1, 0.95)
        elif avg_word_count < 2:
            confidence *= 0.9
        
        # Penalty for too few valid items
        if len(valid_items) < 2:
            confidence *= 0.8
        
        return {
            'valid': True,
            'confidence': confidence,
            'reason': None,
            'severity': None
        }

    @classmethod
    def _is_valid_url(cls, text: str) -> Dict[str, Any]:
        try:
            result = urlparse(str(text))
            if all([result.scheme in ['http', 'https'], result.netloc]):
                # Check for suspicious patterns
                if 'localhost' in result.netloc or '127.0.0.1' in result.netloc:
                    return {
                        'valid': False,
                        'confidence': 0.95,
                        'reason': 'Localhost URL',
                        'severity': 'warning'
                    }
                
                return {
                    'valid': True,
                    'confidence': 0.95,
                    'reason': None,
                    'severity': None
                }
            else:
                return {
                    'valid': False,
                    'confidence': 0.95,
                    'reason': 'Missing scheme or domain',
                    'severity': 'critical'
                }
        except Exception as e:
            return {
                'valid': False,
                'confidence': 1.0,
                'reason': f'URL parsing failed: {str(e)}',
                'severity': 'critical'
            }

    @classmethod
    def _is_generic_valid(cls, value: Any) -> Dict[str, Any]:
        """Fallback validator for unknown fields"""
        text = str(value).strip()
        is_garbage, reason = cls._is_generic_garbage(text)
        
        if is_garbage:
            return {
                'valid': False,
                'confidence': 0.8,
                'reason': reason,
                'severity': 'warning'
            }
        
        return {
            'valid': True,
            'confidence': 0.5,
            'reason': None,
            'severity': None
        }

    @classmethod
    def get_quality_score(cls, item: Dict[str, Any], critical_fields: List[str]) -> Dict[str, Any]:
        """
        Calculate overall quality score for an item.
        
        Returns:
            dict with quality_score, failed_fields, low_confidence_fields,
            needs_llm, and detailed validation results
        """
        results = {}
        failed_fields = []
        low_confidence_fields = []
        critical_failures = []
        warnings = []
        
        for field in critical_fields:
            value = item.get(field)
            result = cls.check(field, value)
            results[field] = result
            
            if not result['valid']:
                failed_fields.append(field)
                if result['severity'] == 'critical':
                    critical_failures.append((field, result['reason']))
                else:
                    warnings.append((field, result['reason']))
            elif result['confidence'] < 0.7:
                low_confidence_fields.append((field, result['confidence'], result.get('reason')))
        
        # Calculate overall quality score
        if not critical_fields:
            quality_score = 0.0
            avg_confidence = 0.0
        else:
            valid_results = [r for r in results.values() if r['valid']]
            if valid_results:
                total_confidence = sum(r['confidence'] for r in valid_results)
                avg_confidence = total_confidence / len(valid_results)
                
                # Penalize for failed fields
                valid_ratio = len(valid_results) / len(critical_fields)
                quality_score = avg_confidence * valid_ratio
            else:
                quality_score = 0.0
                avg_confidence = 0.0
        
        # Decide if LLM is needed
        needs_llm = (
            len(critical_failures) > 0 or  # Any critical failure
            quality_score < 0.6 or  # Overall quality too low
            len(failed_fields) >= len(critical_fields) * 0.3  # 30%+ fields failed
        )
        
        return {
            'quality_score': round(quality_score, 3),
            'avg_confidence': round(avg_confidence, 3),
            'failed_fields': failed_fields,
            'critical_failures': critical_failures,
            'warnings': warnings,
            'low_confidence_fields': low_confidence_fields,
            'needs_llm': needs_llm,
            'llm_priority': 'high' if len(critical_failures) > 0 else 'medium' if needs_llm else 'low',
            'details': results
        }
    
    @classmethod
    def should_full_regenerate(cls, quality_report):
        """
        Decides if the extracted item is so poor that we should discard it 
        and ask the LLM to re-extract EVERYTHING from scratch.
        """
        critical_failures = [f[0] for f in quality_report.get('critical_failures', [])]
        failed_fields = quality_report.get('failed_fields', [])
        score = quality_report.get('quality_score', 1.0)

        # Condition 1: The "Identity" is missing
        # If we don't have a valid Title or Description, the item is fundamentally broken.
        if "title" in critical_failures:
            return True
        if "description" in critical_failures:
            return True

        # Condition 2: Too many holes
        # If 3 or more fields failed validation, it's cleaner to regenerate than patch.
        if len(failed_fields) >= 3:
            return True

        # Condition 3: Overall Garbage
        # If the weighted quality score is abysmal (e.g., < 0.4)
        if score < 0.4:
            return True

        return False