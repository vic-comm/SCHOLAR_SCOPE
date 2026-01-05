import scrapy
from datetime import datetime
import dateparser
import re
from ..utils.django_setup import setup_django
from ..utils.llm_engine import LLMEngine
from ..utils.quality import QualityCheck
from .schemas import ScholarshipScrapedSchema
from pydantic import ValidationError
setup_django()
from scholarships.models import SiteConfig, Scholarship
from scholarships.utils import generate_fingerprint
class ScholarshipBatchSpider(scrapy.Spider):
    name = "scholarship_batch"
    custom_settings = {
            # ✅ Pipeline Path
            "ITEM_PIPELINES": {
                'scholarscope_scrapers.pipelines.RenewalAndDuplicatePipeline': 200,
                "scholarscope_scrapers.scholarscope_scrapers.pipelines.ScholarshipPipeline": 300,
            },
            
            # ✅ Playwright Handlers
            "DOWNLOAD_HANDLERS": {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            
            # 👇 CRITICAL: Switch to Firefox
            "PLAYWRIGHT_BROWSER_TYPE": "firefox",
            
            "PLAYWRIGHT_LAUNCH_OPTIONS": {
                "headless": True,
                "timeout": 60000, # 60s timeout
                # ❌ Removed "args" list (Chrome flags like --disable-http2 are invalid for Firefox)
            },
            
            # 👇 CRITICAL: Firefox Context
            "PLAYWRIGHT_CONTEXT_ARGS": {
                "ignore_https_errors": True, # Ignore SSL/TLS certificate errors
                "java_script_enabled": True,
                "bypass_csp": True,
                
                # ✅ Correct Firefox User Agent
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
                
                "viewport": {"width": 1280, "height": 720},
                "service_workers": "block",
            },

            # ✅ Scrapy Config
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            "LOG_LEVEL": "DEBUG",
            "ROBOTSTXT_OBEY": False,
            "COOKIES_ENABLED": True,
            # Handle 403s so we can see the error pages if they happen
            "HTTPERROR_ALLOWED_CODES": [403, 404, 500],
            
            # 👇 Important: Prevent Scrapy from overriding our Playwright User Agent
            "USER_AGENT": None, 
        }

    def __init__(self, site_config_id=None, scrape_event_id=None, max_items=30, **kwargs):
        super().__init__(**kwargs)
        
        if not site_config_id:
            raise ValueError("⚠ site_config_id is required!")

        # 1. Load Configuration
        self.site_config = SiteConfig.objects.get(id=site_config_id)
        self.start_urls = [self.site_config.list_url]
        self.scrape_event_id = scrape_event_id
        self.max_items = int(max_items)
        self.scraped_count = 0
        self.consecutive_duplicates = 0

        # 2. 👇 CRITICAL FIX: Robust Allowed Domains Logic 👇
        from urllib.parse import urlparse
        
        # Extract the base domain (e.g., 'scholarshipregion.com')
        parsed_base = urlparse(self.site_config.base_url)
        clean_domain = parsed_base.netloc.replace("www.", "")
        
        # Allow both 'example.com' AND 'www.example.com'
        self.allowed_domains = [clean_domain, f"www.{clean_domain}"]
        
        # Also check the list_url just in case it is on a subdomain
        list_domain = urlparse(self.site_config.list_url).netloc.replace("www.", "")
        if list_domain != clean_domain:
            self.allowed_domains.append(list_domain)
            self.allowed_domains.append(f"www.{list_domain}")
            
        print(f"🔓 DEBUG: Allowed Domains set to: {self.allowed_domains}")

        # 3. Load Fingerprints (Optimization)
        self.existing_fingerprints = set(
            Scholarship.objects.values_list("fingerprint", flat=True)
        )
        
        # 4. Initialize AI
        self.llm_engine = LLMEngine()
    
    def extract_section_content(self, response, selector_raw):
        """
        Safely extracts ALL text from a selector string as a clean string.
        """
        if not selector_raw: return None
        
        # 1. Clean the selector (strip invalid Scrapy syntax)
        clean_sel = selector_raw.replace("::text", "").strip()
        
        try:
            # 2. Try getting text directly (fastest)
            text_list = response.css(f"{clean_sel}::text").getall()
            text = " ".join([t.strip() for t in text_list if t.strip()])
            
            # 3. Fallback: Recursively get all text inside elements (best for <li><b>...</b></li>)
            if not text:
                text = response.css(clean_sel).xpath("string(.)").get()
                
            return text.strip() if text else None
        except Exception:
            return None

    def start_requests(self):
        self.logger.error("🔥 start_requests CALLED 🔥")
        yield scrapy.Request(
            self.start_urls[0],
            meta={
                "playwright": True,
                "playwright_page_goto_kwargs": {
                    # 👇 CRITICAL: Don't wait for all network traffic to stop
                    "wait_until": "domcontentloaded", 
                    "timeout": 60000,
                }
            },
            callback=self.parse_list,
        )

    async def parse_list(self, response):
        cfg = self.site_config
        list_item_sel = cfg.list_item_selector
        link_sel = cfg.link_selector
        title_sel = cfg.title_selector
        link_sel_raw = cfg.link_selector.replace("::attr(href)", "").strip()
        title_sel_raw = cfg.title_selector.replace("::text", "").strip()
        for card in response.css(list_item_sel):
            if self.scraped_count >= self.max_items:
                self.logger.info(
                    f"Reached max scrape limit ({self.max_items}) for {self.site_config.name}"
                )
                break

            # Stop if 3 consecutive duplicates
            if self.consecutive_duplicates >= 3:
                self.logger.info(
                    f"⚠ Stopping early after 3 consecutive duplicates for {self.site_config.name}"
                )
                break
            clean_link_sel = link_sel.replace("::attr(href)", "").strip()
            
            relative_link = None
            try:
                # 2. Try extracting via .attrib (The robust way)
                link_el = card.css(link_sel_raw)
                relative_link = link_el.attrib.get('href')
                
                # 3. Fallback: If .attrib failed, try XPath (The "nuclear" way)
                if not relative_link:
                    relative_link = card.css(link_sel_raw).xpath('@href').get()
                    
            except Exception as e:
                self.logger.warning(f"Extraction error for '{clean_link_sel}': {e}")
                continue

            if not relative_link:
                self.logger.warning(f"No link found using selector: {clean_link_sel}")
                continue

            title = None
            try:
                # Try getting text content directly
                # This fetches "My Scholarship Title" from <h2>My Scholarship Title</h2>
                title = card.css(title_sel_raw + "::text").get()
                
                if not title:
                    # Fallback: Sometimes text is nested deep. 'string(.)' gets it all.
                    title = card.css(title_sel_raw).xpath("string(.)").get()
            except:
                pass

            if not relative_link or not title:
                continue

            # title = card.css(f"{title_sel}::text").get()
            url = response.urljoin(relative_link)

            # Compute fingerprint (title + URL hash)
            fingerprint = generate_fingerprint(title, url)

            # Check for duplicate
            if fingerprint in self.existing_fingerprints:
                self.consecutive_duplicates += 1
                self.logger.info(f"⚠ Duplicate #{self.consecutive_duplicates}/3: {title}")
                continue
            else:
                self.consecutive_duplicates = 0
                self.existing_fingerprints.add(fingerprint)

            # Count new scrape
            self.scraped_count += 1

            # Send to detail page
            yield scrapy.Request(
                url,
                meta={
                "playwright": True,
                "fingerprint": fingerprint,
                    "title": title,
                "playwright_page_goto_kwargs": {
                    # 👇 CRITICAL: Don't wait for all network traffic to stop
                    "wait_until": "domcontentloaded", 
                    "timeout": 60000,
                }
            },
                callback=self.parse_detail,
            )
    

    async def parse_detail(self, response):
        cfg = self.site_config


        def safe_parse_date(selector):
            raw = self.extract_section_content(response, selector)
            self.logger.warning(f"📅 RAW_DATE: '{raw}'")
            if not raw: return None
            try:
                dt = dateparser.parse(raw, settings={'STRICT_PARSING': False, 'PREFER_DATES_FROM': 'future'})
                return dt.date() if dt else None
            except:
                return None
        # Extract fields from selectors (fallback to inference if missing)
        title = self.extract_section_content(response, cfg.title_selector)
        description = self.extract_section_content(response, cfg.description_selector)
        reward = self.extract_section_content(response, cfg.reward_selector)
        eligibility = self.extract_eligibility(response, section_text=self.extract_section_content(response, cfg.eligibility_selector))
        requirements = self.extract_requirements(response, section_text=self.extract_section_content(response, cfg.requirements_selector))
        end_date = safe_parse_date(cfg.deadline_selector)
        start_date = safe_parse_date(cfg.start_date_selector)
        tags = self.infer_tags(response, description or "", eligibility or "", requirements or "")
        levels = self.infer_levels(response, description or "", eligibility or "", requirements or "")

        missing_fields = []

        if not QualityCheck.check("title", title): missing_fields.append("title")
        if not QualityCheck.check("requirements", requirements): missing_fields.append("requirements")
        if not QualityCheck.check("reward", reward): missing_fields.append("reward")
        if not QualityCheck.check("end_date", end_date): missing_fields.append("end_date")
        if not QualityCheck.check("start_date", start_date): missing_fields.append("start_date")
        if not QualityCheck.check("tags", tags): missing_fields.append("tags")
        if not QualityCheck.check("levels", levels): missing_fields.append("levels")
        if not QualityCheck.check("eligibility", eligibility): missing_fields.append("eligibility")
        if not QualityCheck.check("description", description): missing_fields.append("description")

        item = {
            "title": title,
            "description": description,
            "reward": reward,
            "link": response.url,
            "end_date": end_date,
            "start_date":start_date,
            "requirements": requirements,
            "eligibility": eligibility,
            "tags": tags,
            "levels": levels,
            "scraped_at": datetime.now().isoformat(),
        }

        if missing_fields:
            if len(missing_fields) > 3 or "description" in missing_fields:
                self.logger.info("Data is too corrupted. Requesting FULL LLM extraction.")
                recovered_data = await self.llm_engine.extract_data(response.text, response.url)
                if isinstance(recovered_data, list):
                    if len(recovered_data) > 0:
                        recovered_data = recovered_data[0] # Take the dictionary out
                    else:
                        recovered_data = {}
                if recovered_data.get("end_date"):
                    recovered_data["end_date"] = dateparser.parse(recovered_data["end_date"]).date()
                if recovered_data.get("start_date"):
                    recovered_data["start_date"] = dateparser.parse(recovered_data["start_date"]).date()
                item.update(recovered_data) 

            else:                
                recovered_data = await self.llm_engine.recover_specific_fields(
                    response.text, missing_fields
                )
                if isinstance(recovered_data, list):
                    if len(recovered_data) > 0:
                        recovered_data = recovered_data[0] # Take the dictionary out
                    else:
                        recovered_data = {}
                if recovered_data.get("end_date"):
                    recovered_data["end_date"] = dateparser.parse(recovered_data["deadline"]).date()
                if recovered_data.get("start_date"):
                    recovered_data["start_date"] = dateparser.parse(recovered_data["start_date"]).date()
                for field in missing_fields:
                    item[field] = recovered_data[field]
        if not item.get("title"):
            # Fallback: Use URL as title so we can identify it later
            item["title"] = f"Unknown Scholarship - {response.url}"
            
        if not item.get("link"):
            item["link"] = response.url
            
        if not item.get("description"):
            item["description"] = "Description unavailable."
            
        if not item.get("scraped_at"):
            item["scraped_at"] = datetime.now().isoformat()

        # B. Ensure List Fields are Lists (Not None)
        for field in ["requirements", "eligibility", "tags", "levels"]:
            if item.get(field) is None:
                item[field] = []
        try:
            valid_item = ScholarshipScrapedSchema(**item)
            yield valid_item.dict()

        except ValidationError as e:
            self.logger.warning(f"Dropping item {item.get('title')}: {e}")


    def infer_levels(self, response, description, eligibility, requirements):
        cfg = self.site_config
        # ✅ Direct DB selector if present
        if cfg.level_selector:
            extracted = response.css(cfg.level_selector).getall()
            cleaned = [x.strip().lower() for x in extracted if x.strip()]
            if cleaned:
                return cleaned

        # ✅ Fallback keyword inference
        if cfg.eligibility_selector == cfg.requirements_selector:
            if cfg.eligibility_selector == cfg.description_selector:
                text = f"{description}".lower()
            else:
                text = f"{description} {requirements}".lower()
        else:
            if cfg.eligibility_selector == cfg.description_selector:
                text = f"{description}".lower()
            else:
                text = f"{description} {requirements} {eligibility}".lower()
        levels = {
            "highschool": ["high school", "secondary", "waec", "ssce", "alevel"],
            "undergraduate": ["undergraduate", "bachelor", "college"],
            "postgraduate": ["postgraduate", "masters", "graduate"],
            "phd": ["phd", "doctorate", "doctoral"],
        }
        detected = [lvl for lvl, keys in levels.items() if any(k in text for k in keys)]
        return detected or ["unspecified"]

    def infer_tags(self, response, description, eligibility, requirements):
        cfg = self.site_config
        # ✅ Direct DB selector if present
        if cfg.tag_selector:
            extracted = response.css(cfg.tag_selector).getall()
            cleaned = [x.strip().lower() for x in extracted if x.strip()]
            if cleaned:
                return cleaned

        # ✅ Fallback
        if cfg.eligibility_selector == cfg.requirements_selector:
            if cfg.eligibility_selector == cfg.description_selector:
                text = f"{description}".lower()
            else:
                text = f"{description} {requirements}".lower()
        else:
            if cfg.eligibility_selector == cfg.description_selector:
                text = f"{description}".lower()
            else:
                text = f"{description} {requirements} {eligibility}".lower()
        tags = {
            "international": ["international", "abroad"],
            "women": ["women", "female", "girls"],
            "stem": ["stem", "engineering", "science"],
            "merit": ["merit", "academic excellence"],
            "need": ["need", "financial aid"],
        }
        detected = [tag for tag, keys in tags.items() if any(k in text for k in keys)]
        return detected or ["general"]
    
    import re

    def extract_requirements(self, response, section_text=None):
        """Extract scholarship requirements/documents needed"""
        requirements = []
        try:
            if section_text:
                clean_text = section_text
                for h in ["Requirements:", "Documents Required:", "What you need:"]:
                    clean_text = clean_text.replace(h, "")
                
                parts = re.split(r'[\n;•►→➤]', clean_text)
                for p in parts:
                    clean_p = p.strip()
                    if self.is_requirement_text(clean_p):
                        requirements.append(clean_p)
            if not requirements:
                cfg = self.site_config
                if cfg.requirements_selector:
                    page_text = " ".join(response.css(cfg.requirements_selector + " *::text").getall())
                elif cfg.description_selector:
                    page_text = " ".join(response.css(cfg.description_selector + " *::text").getall())
                else:
                    page_text = " ".join(response.css("body *::text").getall())
                

                # Common requirement sections
                requirement_patterns = [
                    r'requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'documents?\s*(?:required|needed)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'application\s*requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'needed\s*documents?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'submit[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'must\s*(?:provide|submit|include)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                ]

                # Structured list search
                list_selectors = [
                    'ul li', 'ol li', '.requirements li', '.documents li',
                    '[class*="requirement"] li', '[class*="document"] li'
                ]

                for selector in list_selectors:
                    for el in response.css(selector):
                        text = el.css("::text").get(default="").strip()
                        if self.is_requirement_text(text):
                            requirements.append(text)
                            if len(requirements) >= 10:
                                break
                    if requirements:
                        break

                # Regex fallback
                if not requirements:
                    for pattern in requirement_patterns:
                        matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                        if matches:
                            requirement_text = matches[0].strip()
                            requirements.extend(self.parse_requirement_text(requirement_text))
                            if requirements:
                                break

                # Common keyword fallback
                if not requirements:
                    requirements.extend(self.extract_common_requirements(page_text))

            # Clean + deduplicate
            cleaned = []
            for req in requirements[:10]:
                req = re.sub(r'^[\d\.\)\-\*\•\►\→\➤]\s*', '', req.strip())
                if 10 < len(req) < 200:
                    cleaned.append(req.capitalize())

            return list(dict.fromkeys(cleaned)) or ["Requirements not specified"]

        except Exception as e:
            self.logger.warning(f"Error extracting requirements: {str(e)}")
            return ["Requirements not specified"]


    def extract_eligibility(self, response, section_text=None):
        """Extract scholarship eligibility criteria"""
        eligibility = []
        try:
            if section_text:
                # Clean headers
                clean_text = section_text
                for h in ["Eligibility:", "Who can apply:", "Criteria:"]:
                    clean_text = clean_text.replace(h, "")
                
                # Split by bullets/newlines to find items
                parts = re.split(r'[\n;•►→➤]', clean_text)
                
                # Use your existing validator 'is_eligibility_text'
                for p in parts:
                    clean_p = p.strip()
                    if self.is_eligibility_text(clean_p):
                        eligibility.append(clean_p)
            if not eligibility:
                cfg = self.site_config
                if cfg.eligibility_selector:
                    page_text = " ".join(response.css(cfg.eligibility_selector + " *::text").getall())
                elif cfg.description_selector:
                    page_text = " ".join(response.css(cfg.description_selector + " *::text").getall())
                else:
                    page_text = " ".join(response.css("body *::text").getall())

                eligibility_patterns = [
                    r'eligibility[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'eligible\s*(?:candidates?|applicants?)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'who\s*can\s*apply[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'criteria[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'qualifications?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                    r'must\s*be[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                ]

                list_selectors = [
                    'ul li', 'ol li', '.eligibility li', '.criteria li',
                    '[class*="eligibility"] li', '[class*="criteria"] li',
                    '[class*="qualification"] li',
                ]

                for selector in list_selectors:
                    for el in response.css(selector):
                        text = el.css("::text").get(default="").strip()
                        if self.is_eligibility_text(text):
                            eligibility.append(text)
                            if len(eligibility) >= 10:
                                break
                    if eligibility:
                        break

                if not eligibility:
                    for pattern in eligibility_patterns:
                        matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                        if matches:
                            eligibility_text = matches[0].strip()
                            eligibility.extend(self.parse_eligibility_text(eligibility_text))
                            if eligibility:
                                break

                if not eligibility:
                    eligibility.extend(self.extract_common_eligibility(page_text))

            cleaned = []
            for c in eligibility[:10]:
                c = re.sub(r'^[\d\.\)\-\*\•\►\→\➤]\s*', '', c.strip())
                if 10 < len(c) < 200:
                    cleaned.append(c.capitalize())

            return list(dict.fromkeys(cleaned)) or ["Eligibility criteria not specified"]

        except Exception as e:
            self.logger.warning(f"Error extracting eligibility: {str(e)}")
            return ["Eligibility criteria not specified"]

    def is_requirement_text(self, text):
        keywords = [
            'transcript', 'certificate', 'cv', 'resume', 'letter', 'essay',
            'statement', 'recommendation', 'reference', 'passport', 'photo',
            'application form', 'birth certificate', 'identification',
            'academic record', 'degree', 'diploma', 'ssce', 'upload', 'submit'
        ]
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 200


    def is_eligibility_text(self, text):
        keywords = [
            'citizen', 'age', 'year', 'grade', 'gpa', 'cgpa', 'score',
            'undergraduate', 'graduate', 'student', 'enrolled', 'admitted',
            'nationality', 'resident', 'income', 'female', 'male',
            'minority', 'disability', 'field of study', 'university'
        ]
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 200


    def parse_requirement_text(self, text):
        parts = re.split(r'[\n;•►→➤.!?]', text)
        return [p.strip() for p in parts if self.is_requirement_text(p)]


    def parse_eligibility_text(self, text):
        parts = re.split(r'[\n;•►→➤.!?]', text)
        return [p.strip() for p in parts if self.is_eligibility_text(p)]


    def extract_common_requirements(self, page_text):
        patterns = {
            'Academic Transcript': ['transcript', 'academic record'],
            'CV/Resume': ['cv', 'resume', 'curriculum vitae'],
            'Passport Photograph': ['passport photo', 'recent photo'],
            'Birth Certificate': ['birth certificate'],
            'Letter of Recommendation': ['recommendation letter', 'reference letter'],
            'Statement of Purpose': ['statement of purpose', 'personal statement'],
            'Application Form': ['application form', 'completed form'],
            'Academic Certificates': ['certificate', 'degree certificate'],
            'Identification Document': ['id card', 'identification', 'national id'],
        }
        t = page_text.lower()
        return [name for name, kws in patterns.items() if any(k in t for k in kws)]


    def extract_common_eligibility(self, page_text):
        eligibility = []
        t = page_text.lower()

        age = re.search(r'(?:age|years?)\s*(?:between|from)?\s*(\d+)(?:\s*(?:to|and|-)\s*(\d+))?', t)
        if age:
            if age.group(2):
                eligibility.append(f"Age between {age.group(1)} and {age.group(2)} years")
            else:
                eligibility.append(f"Age {age.group(1)} years or above")

        if 'undergraduate' in t:
            eligibility.append("Must be an undergraduate student")
        if 'postgraduate' in t or 'graduate' in t:
            eligibility.append("Must be a graduate/postgraduate student")
        if 'nigerian' in t and 'citizen' in t:
            eligibility.append("Must be a Nigerian citizen")
        if 'international' in t:
            eligibility.append("Open to international students")
        gpa = re.search(r'(?:gpa|cgpa)\s*(?:of\s*)?(\d+\.?\d*)', t)
        if gpa:
            eligibility.append(f"Minimum GPA/CGPA of {gpa.group(1)}")
        if 'female only' in t:
            eligibility.append("Female students only")
        if 'male only' in t:
            eligibility.append("Male students only")

        return eligibility

