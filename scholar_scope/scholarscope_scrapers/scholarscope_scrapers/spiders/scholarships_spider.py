import scrapy
from datetime import datetime
import dateparser
import re

import trafilatura
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
                'scholarscope_scrapers.scholarscope_scrapers.pipelines.RenewalAndDuplicatePipeline': 200,
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
                "timeout": 60000, 
            },
            
            "PLAYWRIGHT_CONTEXT_ARGS": {
                "ignore_https_errors": True,
                "java_script_enabled": True,
                "bypass_csp": True,
                
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
                
                "viewport": {"width": 1280, "height": 720},
                "service_workers": "block",
            },

            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            "LOG_LEVEL": "DEBUG",
            "ROBOTSTXT_OBEY": False,
            "COOKIES_ENABLED": True,
            "HTTPERROR_ALLOWED_CODES": [403, 404, 500],
            
            "USER_AGENT": None, 
        }

    def __init__(self, site_config_id=None, scrape_event_id=None, max_items=30, **kwargs):
        super().__init__(**kwargs)
        
        if not site_config_id:
            raise ValueError("site_config_id is required!")

        self.site_config = SiteConfig.objects.get(id=site_config_id)
        self.start_urls = [self.site_config.list_url]
        self.scrape_event_id = scrape_event_id
        self.max_items = int(max_items)
        self.scraped_count = 0
        self.consecutive_duplicates = 0

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
            
        print(f"DEBUG: Allowed Domains set to: {self.allowed_domains}")

        # 3. Load Fingerprints (Optimization)
        self.existing_fingerprints = set(
            Scholarship.objects.values_list("fingerprint", flat=True)
        )
        
        # 4. Initialize AI
        self.llm_engine = LLMEngine()
    
   
    def extract_date_from_text(self, page_text, date_type="end"):        
        if date_type == "start":
            patterns = [
                r'application\s*(?:opens?|starts?)[:\s]*([^.!?\n]+)',
                r'opening\s*date[:\s]*([^.!?\n]+)',
                r'start\s*date[:\s]*([^.!?\n]+)',
                r'begins?[:\s]*([^.!?\n]+)',
                r'from[:\s]*([^.!?\n]+?)(?:\s*to\s*|\s*-\s*)',
                r'available\s*from[:\s]*([^.!?\n]+)',
                r'registration\s*(?:opens?|starts?)[:\s]*([^.!?\n]+)'
            ]
        else: # "end" / deadline
            patterns = [
                r'deadline[:\s]*([^.!?\n]+)',
                r'due date[:\s]*([^.!?\n]+)',
                r'closing date[:\s]*([^.!?\n]+)',
                r'last date[:\s]*([^.!?\n]+)',
                r'application closes[:\s]*([^.!?\n]+)',
                r'expires?[:\s]*([^.!?\n]+)',
                r'until[:\s]*([^.!?\n]+)',
                r'by[:\s]*([^.!?\n]+)'
            ]

        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                try:
                    dt = dateparser.parse(
                        date_str, 
                        settings={'STRICT_PARSING': False, 'PREFER_DATES_FROM': 'future'}
                    )
                    if dt:
                        self.logger.info(f"Regex Found {date_type.upper()} Date: {dt.date()} (Match: '{date_str}')")
                        return dt.date()
                except:
                    continue
        return None
    
    def extract_section_content(self, response, selector_raw):
        if not selector_raw: return None
        
        clean_sel = selector_raw.replace("::text", "").strip()
        
        try:
            
            element = response.css(clean_sel).get()
            
            if not element:
                return None

            # 2. Extract text nodes specifically from that one element
            # This handles nested tags (e.g. <h1>Title <span>Part 2</span></h1>) correctly
            text_list = element.css("::text").getall()
            
            text = " ".join([t.strip() for t in text_list if t.strip()])
            
            if not text:
                text = element.xpath("string(.)").get()
                
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
        body_text = self.get_clean_body_text(response)
        def safe_parse_date(selector, date_type="end"):
            raw = self.extract_section_content(response, selector)
            if raw:
                self.logger.debug(f"📅 RAW_DATE ({date_type}): '{raw}'")
                try:
                    dt = dateparser.parse(raw, settings={'STRICT_PARSING': False, 'PREFER_DATES_FROM': 'future'})
                    if dt: 
                        return dt.date()
                except Exception:
                    pass  
            self.logger.info(f"CSS Selector failed for {date_type}. Trying Regex fallback...")
            return self.extract_date_from_text(body_text, date_type)

        title = self.extract_section_content(response, cfg.title_selector)
        if not title:
            title = self.extract_title_from_text(response)
        description = self.extract_section_content(response, cfg.description_selector)
        if not description:
            description = self.extract_description_from_text(response)
        reward = self.extract_section_content(response, cfg.reward_selector)
        if not reward:
            reward = self.extract_reward_from_text(body_text)
            
        eligibility = self.extract_eligibility(response, section_text=self.extract_section_content(response, cfg.eligibility_selector), fallback_text=body_text)
        requirements = self.extract_requirements(response, section_text=self.extract_section_content(response, cfg.requirements_selector), fallback_text=body_text)
        end_date = safe_parse_date(cfg.deadline_selector, 'end')
        start_date = safe_parse_date(cfg.start_date_selector, 'start')
        tags = self.infer_tags(response, description or "", eligibility or "", requirements or "")
        levels = self.infer_levels(response, description or "", eligibility or "", requirements or "")

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

        quality_report = QualityCheck.get_quality_score(item, ["title", "reward", "end_date", "description", "requirements", "eligibility"])
        regenerate_whole = QualityCheck.should_full_regenerate(quality_report)
        if regenerate_whole:
            self.logger.info(f"Data is too corrupted. Requesting FULL LLM extraction. Score: {quality_report['quality_score']}")
            recovered_data = await self.llm_engine.extract_data(response.text, response.url)
            if isinstance(recovered_data, list):
                if len(recovered_data) > 0:
                    recovered_data = recovered_data[0] 
                else:
                    recovered_data = {}
            if recovered_data.get("end_date"):
                recovered_data["end_date"] = dateparser.parse(recovered_data["end_date"]).date()
            if recovered_data.get("start_date"):
                recovered_data["start_date"] = dateparser.parse(recovered_data["start_date"]).date()
            item.update(recovered_data)
        else:
            if quality_report['needs_llm']:
                self.logger.info(f"Triggering AI. Score: {quality_report['quality_score']}")
                
                fields_to_fix = quality_report['failed_fields'] + [x[0] for x in quality_report['low_confidence_fields']]
                fields_to_fix = list(set(fields_to_fix))
                
                if fields_to_fix:
                    self.logger.info(f"Asking Gemini to fix: {fields_to_fix}")
                    recovered_data = await self.llm_engine.recover_specific_fields(body_text, fields_to_fix)
                    if recovered_data.get("end_date"):
                        recovered_data["end_date"] = dateparser.parse(recovered_data["end_date"]).date()
            
        # if missing_fields:
        #     if len(missing_fields) > 3 or "description" in missing_fields:
        #         self.logger.info("Data is too corrupted. Requesting FULL LLM extraction.")
        #         recovered_data = await self.llm_engine.extract_data(response.text, response.url)
        #         if isinstance(recovered_data, list):
        #             if len(recovered_data) > 0:
        #                 recovered_data = recovered_data[0] # Take the dictionary out
        #             else:
        #                 recovered_data = {}
        #         if recovered_data.get("end_date"):
        #             recovered_data["end_date"] = dateparser.parse(recovered_data["end_date"]).date()
        #         if recovered_data.get("start_date"):
        #             recovered_data["start_date"] = dateparser.parse(recovered_data["start_date"]).date()
        #         item.update(recovered_data) 

        #     else:                
        #         recovered_data = await self.llm_engine.recover_specific_fields(
        #             response.text, missing_fields
        #         )
        #         if isinstance(recovered_data, list):
        #             if len(recovered_data) > 0:
        #                 recovered_data = recovered_data[0] # Take the dictionary out
        #             else:
        #                 recovered_data = {}
        #         if recovered_data.get("end_date"):
        #             recovered_data["end_date"] = dateparser.parse(recovered_data["deadline"]).date()
        #         if recovered_data.get("start_date"):
        #             recovered_data["start_date"] = dateparser.parse(recovered_data["start_date"]).date()
        #         for field in missing_fields:
        #             item[field] = recovered_data[field]


        if not item.get("title"):
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
        # Direct DB selector if present
        if cfg.level_selector:
            extracted = response.css(cfg.level_selector).getall()
            cleaned = [x.strip().lower() for x in extracted if x.strip()]
            if cleaned:
                return cleaned

        # Fallback keyword inference
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
        if not detected:
            return self.extract_tags_from_text(response)
        return detected or ["general"]
    

    def extract_requirements(self, response, section_text=None, fallback_text=None):
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
            if not cleaned:
                return self.extract_requirements_from_text(response, fallback_text)
            return list(dict.fromkeys(cleaned)) or ["Requirements not specified"]

        except Exception as e:
            self.logger.warning(f"Error extracting requirements: {str(e)}")
            return ["Requirements not specified"]


    def extract_eligibility(self, response, section_text=None, fallback_text=None):
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
            if not cleaned:
                self.extract_eligibility_from_text(response, fallback_text)
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

    def get_clean_body_text(self, response):
        try:
            text = trafilatura.extract(response.text)
            if text and len(text) > 200: # Ensure we got a decent chunk
                return text
        except: pass
        
    
        content_selectors = [
            "article",                # HTML5 Standard
            ".entry-content",         # WordPress Standard
            ".post-content",          # Common Theme
            ".article-content",       # Common
            "main",                   # HTML5 Standard
            "#content",               # Old Standard
            "div[class*='content']",  # Fuzzy match
        ]

        for sel in content_selectors:
            elements = response.css(sel)
            for el in elements:
                text = self._extract_text_excluding_noise(el)
                if text and len(text) > 500:
                    return text

        return self._extract_text_excluding_noise(response.css("body"))

    def _extract_text_excluding_noise(self, selector):
        try:
            clean_xpath = """
                descendant-or-self::text()
                [not(ancestor::script)]
                [not(ancestor::style)]
                [not(ancestor::nav)]
                [not(ancestor::footer)]
                [not(ancestor::aside)]
                [not(ancestor::div[contains(@class, 'related')])]
                [not(ancestor::div[contains(@class, 'sidebar')])]
                [not(ancestor::div[contains(@class, 'widget')])]
                [not(ancestor::div[contains(@class, 'comments')])]
            """
            
            text_list = selector.xpath(clean_xpath).getall()
            full_text = " ".join([t.strip() for t in text_list if t.strip()])
            return re.sub(r'\s+', ' ', full_text).strip()
        except:
            return selector.xpath("string(.)").get()

    # ---------------------------------------------------------
    # 1. REQUIREMENTS
    # ---------------------------------------------------------
    def extract_requirements_from_text(self, response, fallback_text=None):
        """Extract scholarship requirements/documents needed"""
        try:
           
            page_text = fallback_text if fallback_text else self.get_clean_body_text(response)
            requirements = []
            
            requirement_patterns = [
                r'requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'documents?\s*(?:required|needed)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'application\s*requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'needed\s*documents?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'submit[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'must\s*(?:provide|submit|include)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)'
            ]
            
            # 1. Try Structured Lists (CSS Selectors)
            list_selectors = [
                'ul li', 'ol li', '.requirements li', '.documents li',
                '[class*="requirement"] li', '[class*="document"] li'
            ]
            
            for selector in list_selectors:
                elements = response.css(selector)
                temp_reqs = []
                for element in elements:
                    # xpath("string(.)") gets text from <li> and its children <b>, <span> etc.
                    text = element.xpath("string(.)").get(default="").strip()
                    if self.is_requirement_text(text):
                        temp_reqs.append(text)
                        if len(temp_reqs) >= 10: break
                
                if temp_reqs:
                    requirements = temp_reqs
                    break
            
            # 2. Regex Fallback
            if not requirements:
                for pattern in requirement_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        requirement_text = matches[0].strip()
                        requirements.extend(self.parse_requirement_text(requirement_text))
                        if requirements: break
            
            # 3. Keyword Fallback
            if not requirements:
                requirements.extend(self.extract_common_requirements(page_text))
            
            # Cleaning
            cleaned_requirements = []
            for req in requirements[:10]:
                req = req.strip()
                if len(req) > 10 and len(req) < 200:
                    req = re.sub(r'^[\d\.\)\-\*\•\►\→\➤]\s*', '', req)
                    req = re.sub(r'^\w\)\s*', '', req)
                    cleaned_requirements.append(req.strip())
            
            return cleaned_requirements if cleaned_requirements else ["Requirements not specified"]
            
        except Exception as e:
            self.logger.warning(f"Error extracting requirements: {str(e)}")
            return ["Requirements not specified"]

    # ---------------------------------------------------------
    # 2. LEVELS
    # ---------------------------------------------------------
    def extract_levels(self, response):
        """Extract education levels"""
        try:
            page_text = self.get_clean_body_text(response).lower()
            title_text = (response.css("title::text").get() or "").lower()
            
            all_text = f"{page_text} {title_text}"
            levels = set()

            level_keywords = {
                "highschool": ["secondary school", "high school", "ssce", "waec", "neco", "alevel", "k12"],
                "undergraduate": ["undergraduate", "bachelor", "bsc", "ba", "first degree", "college student"],
                "postgraduate": ["postgraduate", "masters", "msc", "ma", "mphil", "graduate school"],
                "phd": ["phd", "doctorate", "doctoral", "dphil", "research degree"],
            }

            for level, keywords in level_keywords.items():
                if any(keyword in all_text for keyword in keywords):
                    levels.add(level)

            # Check Meta Description
            meta_desc = response.css('meta[name="description"]::attr(content)').get()
            if meta_desc:
                desc_content = meta_desc.lower()
                for level, keywords in level_keywords.items():
                    if any(keyword in desc_content for keyword in keywords):
                        levels.add(level)

            if not levels:
                levels.add("unspecified")

            return list(levels)

        except Exception as e:
            self.logger.warning(f"Error extracting levels: {str(e)}")
            return ["unspecified"]

    # ---------------------------------------------------------
    # 3. ELIGIBILITY
    # ---------------------------------------------------------
    def extract_eligibility_from_text(self, response, section_text=None):
        """Extract scholarship eligibility criteria"""
        try:
            page_text = section_text if section_text else self.get_clean_body_text(response)
            eligibility = []
            
            eligibility_patterns = [
                r'eligibility[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'eligible\s*(?:candidates?|applicants?)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'who\s*can\s*apply[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'criteria[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'qualifications?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'must\s*be[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)'
            ]
            
            # 1. Structured Lists
            list_selectors = [
                'ul li', 'ol li', '.eligibility li', '.criteria li',
                '[class*="eligibility"] li', '[class*="criteria"] li', '[class*="qualification"] li'
            ]
            
            for selector in list_selectors:
                elements = response.css(selector)
                temp_elig = []
                for element in elements:
                    text = element.xpath("string(.)").get(default="").strip()
                    if self.is_eligibility_text(text):
                        temp_elig.append(text)
                        if len(temp_elig) >= 10: break
                
                if temp_elig:
                    eligibility = temp_elig
                    break
            
            # 2. Pattern Matching
            if not eligibility:
                for pattern in eligibility_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        eligibility_text = matches[0].strip()
                        eligibility.extend(self.parse_eligibility_text(eligibility_text))
                        if eligibility: break
            
            # 3. Common Keywords
            if not eligibility:
                eligibility.extend(self.extract_common_eligibility(page_text))
            
            cleaned_eligibility = []
            for criteria in eligibility[:10]:
                criteria = criteria.strip()
                if len(criteria) > 10 and len(criteria) < 200:
                    criteria = re.sub(r'^[\d\.\)\-\*\•\►\→\➤]\s*', '', criteria)
                    criteria = re.sub(r'^\w\)\s*', '', criteria)
                    cleaned_eligibility.append(criteria.strip())
            
            return cleaned_eligibility if cleaned_eligibility else ["Eligibility criteria not specified"]
            
        except Exception as e:
            self.logger.warning(f"Error extracting eligibility: {str(e)}")
            return ["Eligibility criteria not specified"]

    # ---------------------------------------------------------
    # 4. TAGS
    # ---------------------------------------------------------
    def normalize(self, text: str):
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def extract_tags_from_text(self, response):
        """Extract tags"""
        try:
            from difflib import get_close_matches # Ensure import
            
            page_text = self.normalize(self.get_clean_body_text(response))
            title_text = self.normalize(response.css("title::text").get() or "")
            all_text = f"{page_text} {title_text}"

            tags = set()
            tag_keywords = {
                'international': ['international', 'global', 'worldwide', 'abroad', "foreign"],
                'merit': ['merit', 'academic excellence', 'outstanding', 'scholarly'],
                'need': ['need', 'financial aid', 'low income', 'need-based', 'scholarship for poor'],
            }

            # 1. Keyword Scan
            for tag, keywords in tag_keywords.items():
                for kw in keywords:
                    if kw in all_text:
                        tags.add(tag)
                        break

            # 2. Meta Keywords
            meta_keywords = response.css('meta[name="keywords"]::attr(content)').get()
            if meta_keywords:
                keywords_content = self.normalize(meta_keywords)
                meta_tags = [kw.strip() for kw in keywords_content.split(",")]
                for mt in meta_tags:
                    for key in tag_keywords.keys():
                        if get_close_matches(mt, [key], n=1, cutoff=0.8):
                            tags.add(key)

            # 3. Tag Elements
            tag_selectors = ['.tags a', '.categories a', '.tag', '.category', '[class*="tag"]', '[class*="category"]']
            for selector in tag_selectors:
                elements = response.css(selector)
                for element in elements[:5]:
                    tag_text = self.normalize(element.xpath("string(.)").get(default=""))
                    for key, keywords in tag_keywords.items():
                        if tag_text in keywords or get_close_matches(tag_text, keywords, n=1, cutoff=0.8):
                            tags.add(key)

            return list(tags) if tags else ['general']

        except Exception as e:
            self.logger.warning(f"Error extracting tags: {str(e)}")
            return ['general']

    # ---------------------------------------------------------
    # 5. TITLE
    # ---------------------------------------------------------
    def extract_title_from_text(self, response):
        """Extract scholarship title"""
        selectors = ["h1", ".entry-title", ".post-title", ".scholarship-title", "[class*='title']"]
        
        for selector in selectors:
            title = response.css(f"{selector}::text").get()
            if title and len(title.strip()) > 5:
                title = title.split('|')[0].strip()
                title = title.split(' - ')[0].strip()
                return title[:255]
        
        # Fallback to page title
        page_title = response.css("title::text").get()
        if page_title:
            return page_title.split('|')[0].strip()[:255]
            
        return "Scholarship Title Not Found"

    # ---------------------------------------------------------
    # 6. DESCRIPTION
    # ---------------------------------------------------------
    def extract_description_from_text(self, response):
        """Extract scholarship description"""
        description_parts = []
        
        # 1. Meta Description
        meta_desc = response.css('meta[name="description"]::attr(content)').get()
        if meta_desc and len(meta_desc) > 50:
            description_parts.append(meta_desc.strip())
        
        # 2. First few paragraphs
        paragraphs = response.css("p")
        content_paragraphs = []
        for p in paragraphs[:5]:
            text = p.xpath("string(.)").get(default="").strip()
            if len(text) > 50:
                skip_words = ['home', 'menu', 'navigation', 'copyright', 'privacy', 'cookie']
                if not any(skip_word in text.lower() for skip_word in skip_words):
                    content_paragraphs.append(text)
                    if len(content_paragraphs) >= 2: break
        
        if content_paragraphs:
            description_parts.extend(content_paragraphs)
        
        # 3. Article Content (if nothing else found)
        if not description_parts:
            article_selectors = ['.entry-content', '.post-content', '.article-content', 'article']
            for selector in article_selectors:
                text = response.css(selector).xpath("string(.)").get()
                if text and len(text.strip()) > 100:
                    description_parts.append(text.strip()[:500])
                    break
        
        if description_parts:
            description = ' '.join(description_parts)
            description = re.sub(r'\s+', ' ', description)
            return description
        
        return "No description available"

    # ---------------------------------------------------------
    # 7. REWARD
    # ---------------------------------------------------------
    def extract_reward_from_text(self, response):
        """Extract scholarship reward/amount"""
        try:
            page_text = self.get_clean_body_text(response)
            
            naira_patterns = [r'₦\s*([0-9,]+(?:\.[0-9]{2})?)', r'N\s*([0-9,]+(?:\.[0-9]{2})?)', r'([0-9,]+(?:\.[0-9]{2})?)\s*naira']
            usd_patterns = [r'\$\s*([0-9,]+(?:\.[0-9]{2})?)', r'([0-9,]+(?:\.[0-9]{2})?)\s*(?:USD|dollars?)']
            general_patterns = [r'worth\s*(?:of\s*)?₦?\$?\s*([0-9,]+)', r'value\s*(?:of\s*)?₦?\$?\s*([0-9,]+)', r'amount\s*(?:of\s*)?₦?\$?\s*([0-9,]+)']
            
            all_patterns = naira_patterns + usd_patterns + general_patterns
            
            for pattern in all_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple): match = match[0]
                        try:
                            num_value = float(match.replace(',', ''))
                            if num_value > 1000:
                                return f"₦{match}" if any(p in pattern for p in naira_patterns) else f"${match}"
                        except: continue
            
            reward_keywords = ['tuition', 'allowance', 'stipend', 'support', 'funding', 'full scholarship']
            for keyword in reward_keywords:
                if keyword in page_text.lower():
                    return f"Educational {keyword}"
            
            return "Amount not specified"
        except:
            return "Amount not specified"

    # ---------------------------------------------------------
    # UTILITY FUNCTIONS (Keep these as they were)
    # ---------------------------------------------------------
    def is_requirement_text(self, text):
        keywords = ['transcript', 'certificate', 'cv', 'resume', 'letter', 'essay', 'statement', 'recommendation', 'reference', 'passport', 'photo', 'application form', 'birth certificate', 'identification', 'academic record', 'degree', 'diploma', 'waec', 'jamb', 'ssce', 'bank statement', 'financial', 'medical report', 'upload', 'submit']
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 200

    def is_eligibility_text(self, text):
        keywords = ['citizen', 'age', 'year', 'grade', 'gpa', 'cgpa', 'score', 'level', 'undergraduate', 'graduate', 'student', 'enrolled', 'admitted', 'nationality', 'resident', 'income', 'family', 'female', 'male', 'minority', 'disability', 'field of study', 'department', 'faculty', 'university', 'college']
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 200

    def parse_requirement_text(self, text):
        requirements = []
        delimiters = ['\n', ';', '•', '►', '→', '➤']
        for d in delimiters:
            if d in text:
                return [p.strip() for p in text.split(d) if self.is_requirement_text(p.strip())]
        sentences = re.split(r'[.!?]', text)
        return [s.strip() for s in sentences if self.is_requirement_text(s.strip())] or [text.strip()]

    def parse_eligibility_text(self, text):
        eligibility = []
        delimiters = ['\n', ';', '•', '►', '→', '➤']
        for d in delimiters:
            if d in text:
                return [p.strip() for p in text.split(d) if self.is_eligibility_text(p.strip())]
        sentences = re.split(r'[.!?]', text)
        return [s.strip() for s in sentences if self.is_eligibility_text(s.strip())] or [text.strip()]

    def extract_common_requirements(self, page_text):
        requirements = []
        t = page_text.lower()
        patterns = {
            'Academic Transcript': ['transcript', 'academic record'],
            'CV/Resume': ['cv', 'resume', 'curriculum vitae'],
            'Passport Photograph': ['passport photo', 'recent photo'],
            'Birth Certificate': ['birth certificate'],
            'Letter of Recommendation': ['recommendation letter', 'reference letter'],
            'Statement of Purpose': ['statement of purpose', 'personal statement'],
            'Application Form': ['application form', 'completed form'],
            'Academic Certificates': ['certificate', 'degree certificate'],
            'Identification Document': ['id card', 'identification', 'national id']
        }
        for name, kws in patterns.items():
            if any(k in t for k in kws): requirements.append(name)
        return requirements

    def extract_common_eligibility(self, page_text):
        eligibility = []
        t = page_text.lower()
        age = re.search(r'(?:age|years?)\s*(?:between|from)?\s*(\d+)(?:\s*(?:to|and|-)\s*(\d+))?', t)
        if age:
            if age.group(2): eligibility.append(f"Age between {age.group(1)} and {age.group(2)} years")
            else: eligibility.append(f"Age {age.group(1)} years or above")
        
        if 'undergraduate' in t: eligibility.append("Must be an undergraduate student")
        if 'postgraduate' in t or 'graduate' in t: eligibility.append("Must be a graduate/postgraduate student")
        if 'nigerian' in t and 'citizen' in t: eligibility.append("Must be a Nigerian citizen")
        if 'international' in t: eligibility.append("Open to international students")
        gpa = re.search(r'(?:gpa|cgpa)\s*(?:of\s*)?(\d+\.?\d*)', t)
        if gpa: eligibility.append(f"Minimum GPA/CGPA of {gpa.group(1)}")
        if 'female only' in t: eligibility.append("Female students only")
        if 'male only' in t: eligibility.append("Male students only")
        return eligibility