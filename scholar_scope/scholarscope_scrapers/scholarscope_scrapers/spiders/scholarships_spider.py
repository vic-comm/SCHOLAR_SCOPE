import scrapy
from datetime import datetime
import re
from ..utils.django_setup import setup_django
setup_django()
from scholarships.models import SiteConfig, Scholarship
from scholarships.utils import generate_fingerprint
# class ScholarshipBatchSpider(scrapy.Spider):
#     name = "scholarship_batch"
#     custom_settings = {"PLAYWRIGHT_BROWSER_TYPE": "chromium"}

#     def start_requests(self):
#         for domain, config in SITE_CONFIGS.items():
#             list_page = config.get("list_page", {})
#             for url in list_page.get("urls", []):
#                 yield scrapy.Request(
#                     url,
#                     meta={"playwright": True, "domain": domain},
#                     callback=self.parse_list,
#                 )

#     async def parse_list(self, response):
#         domain = response.meta.get("domain")
#         config = SITE_CONFIGS.get(domain, {}).get("list_page", {})
#         link_selector = config.get("link_selector")

#         if not link_selector:
#             self.logger.warning(f"No link selector found for {domain}")
#             return

#         links = response.css(link_selector).getall()
#         for link in links:
#             absolute = response.urljoin(link)
#             yield scrapy.Request(
#                 absolute,
#                 meta={"playwright": True, "domain": domain},
#                 callback=self.parse_detail,
#             )

#     async def parse_detail(self, response):
#         domain = response.meta.get("domain")
#         config = SITE_CONFIGS.get(domain, {}).get("detail_page", {})

#         def get_text(selector):
#             """Extracts all text joined cleanly or empty string if selector missing."""
#             if not selector:
#                 return ""
#             return " ".join([x.strip() for x in response.css(selector).getall() if x.strip()])

#         # Extract core fields
#         title = get_text(config.get("title"))
#         description = get_text(config.get("description"))
#         reward = get_text(config.get("reward"))
#         eligibility = get_text(config.get("eligibility"))
#         requirements = get_text(config.get("requirements"))
#         start_date = get_text(config.get("start_date"))
#         end_date = get_text(config.get("end_date"))

#         # Inference based on relevant sections only
#         tags = self.infer_tags(response, description, eligibility, requirements)
#         levels = self.infer_levels(response, description, eligibility, requirements)

#         yield {
#             "title": title,
#             "description": description,
#             "reward": reward,
#             "link": response.url,
#             "start_date": start_date,
#             "end_date": end_date,
#             "requirements": requirements,
#             "eligibility": eligibility,
#             "tags": tags,
#             "level": levels,
#             "scraped_at": datetime.now().isoformat(),
#         }

#     def infer_levels(self, response, description, eligibility, requirements):
#         """Infer education levels — priority: selector → fallback to keyword inference."""

#         # ✅ 1️⃣ Check if site-config provides level selector
#         level_selector = self.site_config.get("level_selector")
#         if level_selector:
#             level_elements = response.css(level_selector).getall()
#             cleaned_levels = [lvl.strip().lower() for lvl in level_elements if lvl.strip()]
#             if cleaned_levels:
#                 return cleaned_levels  # ✅ Return directly if site explicitly provides levels

#         # ✅ 2️⃣ Fallback: infer from description-based text
#         combined_text = f"{description} {eligibility} {requirements}".lower()

#         level_keywords = {
#             "highschool": ["secondary school", "high school", "ssce", "waec", "neco", "alevel"],
#             "undergraduate": ["undergraduate", "bachelor", "bsc", "ba", "first degree", "college student"],
#             "postgraduate": ["postgraduate", "masters", "msc", "ma", "mphil", "graduate school"],
#             "phd": ["phd", "doctorate", "doctoral", "dphil", "research degree"],
#         }

#         detected = [
#             level for level, kws in level_keywords.items()
#             if any(kw in combined_text for kw in kws)
#         ]
#         return detected or ["unspecified"]


#     def infer_tags(self, response, description, eligibility, requirements):
#         """Infer scholarship tags — priority: selector → fallback to keyword inference."""

#         # ✅ 1️⃣ Check if site-config provides tag selector
#         tag_selector = self.site_config.get("tag_selector")
#         if tag_selector:
#             tag_elements = response.css(tag_selector).getall()
#             cleaned_tags = [tag.strip().lower() for tag in tag_elements if tag.strip()]
#             if cleaned_tags:
#                 return cleaned_tags  # ✅ Return immediately if selector yields usable tags

#         # ✅ 2️⃣ Fallback: keyword inference
#         combined_text = f"{description} {eligibility} {requirements}".lower()

#         tag_keywords = {
#             "international": ["international", "global", "worldwide", "abroad", "foreign"],
#             "merit": ["merit", "academic excellence", "outstanding", "scholarly"],
#             "need": ["need", "financial aid", "low income", "need-based", "disadvantaged"],
#             "women": ["women", "female", "girls"],
#             "stem": ["science", "engineering", "technology", "mathematics", "stem"],
#         }

#         detected = [
#             tag for tag, kws in tag_keywords.items()
#             if any(kw in combined_text for kw in kws)
#         ]
#         return detected or ["general"]
  # ✅ Import your model


class ScholarshipBatchSpider(scrapy.Spider):
    name = "scholarship_batch"
    custom_settings = {"PLAYWRIGHT_BROWSER_TYPE": "chromium"}

    def __init__(self, site_config_id=None, scrape_event_id=None, max_items=30, **kwargs):
        super().__init__(**kwargs)
        if not site_config_id:
            raise ValueError("⚠ site_config_id is required!")

        self.site_config = SiteConfig.objects.get(id=site_config_id)
        self.start_urls = [self.site_config.list_url]
        self.scrape_event_id = scrape_event_id
        self.max_items = int(max_items)
        self.scraped_count = 0
        self.consecutive_duplicates = 0

        # Preload fingerprints of existing scholarships
        self.existing_fingerprints = set(
            Scholarship.objects.values_list("fingerprint", flat=True)
        )

    def start_requests(self):
        yield scrapy.Request(
            self.start_urls[0],
            meta={"playwright": True},
            callback=self.parse_list,
        )

    async def parse_list(self, response):
        cfg = self.site_config
        list_item_sel = cfg.list_item_selector
        link_sel = cfg.link_selector
        title_sel = cfg.title_selector

        for card in response.css(list_item_sel):
            # Stop if reached limit
            if self.scraped_count >= self.max_items:
                self.logger.info(
                    f"✅ Reached max scrape limit ({self.max_items}) for {self.site_config.name}"
                )
                break

            # Stop if 3 consecutive duplicates
            if self.consecutive_duplicates >= 3:
                self.logger.info(
                    f"⚠ Stopping early after 3 consecutive duplicates for {self.site_config.name}"
                )
                break

            # Extract link and title
            relative_link = card.css(f"{link_sel}::attr(href)").get()
            title = card.css(f"{title_sel}::text").get()
            if not relative_link or not title:
                continue

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
                },
                callback=self.parse_detail,
            )
    

    async def parse_detail(self, response):
        cfg = self.site_config

        def extract(selector):
            if not selector:
                return None
            return " ".join(
                [txt.strip() for txt in response.css(selector).getall() if txt.strip()]
            )

        # ✅ Extract fields from selectors (fallback to inference if missing)
        title = extract(cfg.title_selector)
        description = extract(cfg.description_selector)
        reward = extract(cfg.reward_selector)
        eligibility = self.extract_eligibility(extract(cfg.eligibility_selector))
        requirements = self.extract_requirements(extract(cfg.requirements_selector))
        end_date = self.parse_date_string(extract(cfg.deadline_selector))
        start_date = self.parse_date_string(extract(cfg.start_date_selector))
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

        yield item

    def parse_date_string(self, date_str):
        """Parse date string to datetime object"""
        date_str = date_str.strip()
        
        # Remove common prefixes/suffixes
        date_str = re.sub(r'^(on|by|from|until|before|after)\s+', '', date_str, flags=re.IGNORECASE)
        date_str = re.sub(r'\s+(onwards?|forward)$', '', date_str, flags=re.IGNORECASE)
        
        # Common date formats
        date_formats = [
            '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d',
            '%d-%m-%Y', '%B %d, %Y', '%d %B %Y',
            '%b %d, %Y', '%d %b %Y', '%Y/%m/%d',
            '%d.%m.%Y', '%Y.%m.%d'
        ]
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.dat()
            except:
                continue
        
        return None

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

# ===============================
# 🧠 REQUIREMENTS EXTRACTOR
# ===============================
    def extract_requirements(self, response):
        """Extract scholarship requirements/documents needed"""
        try:
            cfg = self.site_config
            if cfg.requirements_selector:
                page_text = " ".join(response.css(cfg.requirements_selector + " *::text").getall())
            elif cfg.description_selector:
                page_text = " ".join(response.css(cfg.description_selector + " *::text").getall())
            else:
                page_text = " ".join(response.css("body *::text").getall())
            requirements = []

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


    # ===============================
    # 🧠 ELIGIBILITY EXTRACTOR
    # ===============================
    def extract_eligibility(self, response):
        """Extract scholarship eligibility criteria"""
        try:
            cfg = self.site_config
            if cfg.eligibility_selector:
                page_text = " ".join(response.css(cfg.eligibility_selector + " *::text").getall())
            elif cfg.description_selector:
                page_text = " ".join(response.css(cfg.description_selector + " *::text").getall())
            else:
                page_text = " ".join(response.css("body *::text").getall())
            eligibility = []

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

