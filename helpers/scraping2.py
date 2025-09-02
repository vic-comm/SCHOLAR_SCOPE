import re
import time
from datetime import datetime
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from bs4 import BeautifulSoup

class ScholarshipScraper:
    def __init__(self, headless=True, chrome_driver_path=None, max_retries=2):
        self.driver = None
        self.headless = headless
        self.chrome_driver_path = chrome_driver_path
        self.max_retries = max_retries

    def connect_browser(self):
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1920,1080")

        if self.chrome_driver_path:
            self.driver = webdriver.Chrome(options=options, service=Service(self.chrome_driver_path))
        else:
            self.driver = webdriver.Chrome(options=options)

        # Hide webdriver
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def quit_browser(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_page(self, url):
        """Load page and return BeautifulSoup object"""
        self.connect_browser()
        for attempt in range(self.max_retries):
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                html = self.driver.page_source
                return BeautifulSoup(html, "html.parser")
            except TimeoutException:
                time.sleep(2)
        return None

    def extract_title(self, soup):
        selectors = ["h1", ".entry-title", ".post-title", ".scholarship-title"]
        for sel in selectors:
            el = soup.select_one(sel)
            if el and el.text.strip():
                title = el.text.split("|")[0].split(" - ")[0].strip()
                return title[:255]
        return soup.title.text.strip()[:255] if soup.title else "Title not found"

    def extract_description(self, soup):
        desc_parts = []

        # Meta description
        meta = soup.select_one('meta[name="description"]')
        if meta and meta.get("content"):
            desc_parts.append(meta["content"].strip())

        # Paragraphs
        paragraphs = soup.select("p")
        for p in paragraphs[:5]:
            text = p.text.strip()
            if len(text) > 50:
                desc_parts.append(text)

        # Article content
        for sel in [".entry-content", ".post-content", ".article-content", "article"]:
            el = soup.select_one(sel)
            if el and len(el.text.strip()) > 100:
                desc_parts.append(el.text.strip()[:500])
                break

        return " ".join(desc_parts) if desc_parts else "No description available"

    def extract_dates(self, soup):
        body_text = soup.get_text(" ", strip=True)
        start_patterns = [
            r"(?:opens?|starts?)[:\s]*([^\n\.]+)",
            r"start date[:\s]*([^\n\.]+)",
        ]
        end_patterns = [
            r"(?:deadline|due date|closes?)[:\s]*([^\n\.]+)",
            r"end date[:\s]*([^\n\.]+)"
        ]
        def parse_date(patterns):
            for pat in patterns:
                m = re.search(pat, body_text, re.I)
                if m:
                    return self.parse_date_string(m.group(1).strip())
            return None

        return parse_date(start_patterns), parse_date(end_patterns)

    def extract_reward(self, soup):
        text = soup.get_text(" ", strip=True)
        patterns = [
            r"₦\s*([\d,]+)", r"N\s*([\d,]+)", r"\$\s*([\d,]+)", r"([0-9,]+)\s*(?:USD|dollars?)"
        ]
        for pat in patterns:
            m = re.findall(pat, text)
            if m:
                return m[0]
        return "Amount not specified"

    def extract_application_link(self, soup, base_url=None):
        # Try links/buttons
        links = soup.select("a[href*='apply'], a[href*='application']")
        for link in links:
            href = link.get("href")
            if href:
                return urljoin(base_url, href) if base_url else href
        return "Application link not found"

    def extract_requirements(self, soup):
        reqs = []
        for sel in ["ul li", "ol li", ".requirements li"]:
            for li in soup.select(sel):
                text = li.text.strip()
                if text:
                    reqs.append(text)
        return reqs or ["Requirements not specified"]

    def extract_eligibility(self, soup):
        elig = []
        for sel in ["ul li", "ol li", ".eligibility li", ".criteria li"]:
            for li in soup.select(sel):
                text = li.text.strip()
                if text:
                    elig.append(text)
        return elig or ["Eligibility criteria not specified"]

    def extract_tags(self, soup):
        tags = set()
        for sel in [".tags a", ".categories a"]:
            for el in soup.select(sel):
                tag = el.text.strip().lower()
                if tag:
                    tags.add(tag)
        return list(tags) or ["general"]

    def parse_date_string(self, date_str):
        date_str = re.sub(r"(on|by|from|until)\s+", "", date_str, flags=re.I)
        formats = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%d %B %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        return None

    def scrape_scholarship(self, url):
        soup = self.scrape_page(url)
        if not soup:
            return None
        start_date, end_date = self.extract_dates(soup)
        return {
            "title": self.extract_title(soup),
            "description": self.extract_description(soup),
            "reward": self.extract_reward(soup),
            "application_link": self.extract_application_link(soup, base_url=url),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "requirements": self.extract_requirements(soup),
            "eligibility": self.extract_eligibility(soup),
            "tags": self.extract_tags(soup),
            "scraped_at": datetime.now().isoformat()
        }

import time
import re
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup

class ScholarshipListScraper:
    def __init__(self, headless=True, chrome_driver_path=None, max_retries=2):
        self.driver = None
        self.base_url = None
        self.headless = headless
        self.chrome_driver_path = chrome_driver_path
        self.max_retries = max_retries

    def connect_browser(self):
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1920,1080")

        if self.chrome_driver_path:
            self.driver = webdriver.Chrome(options=options, service=Service(self.chrome_driver_path))
        else:
            self.driver = webdriver.Chrome(options=options)

        # Anti-detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def quit_browser(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def load_page(self, url):
        self.connect_browser()
        for _ in range(self.max_retries):
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                html = self.driver.page_source
                return BeautifulSoup(html, "html.parser")
            except TimeoutException:
                time.sleep(2)
        return None

    def scrape_scholarship_list(self, list_url, max_scholarships=None):
        self.base_url = f"{urlparse(list_url).scheme}://{urlparse(list_url).netloc}"
        all_scholarships = []
        current_url = list_url
        page_num = 1

        while current_url:
            print(f"Scraping page {page_num}: {current_url}")
            soup = self.load_page(current_url)
            if not soup:
                break

            links = self.extract_scholarship_links(soup)
            all_scholarships.extend(links)

            if max_scholarships and len(all_scholarships) >= max_scholarships:
                all_scholarships = all_scholarships[:max_scholarships]
                break

            next_page_url = self.find_next_page(soup)
            current_url = urljoin(self.base_url, next_page_url) if next_page_url else None
            page_num += 1
            time.sleep(2)

        return all_scholarships

    def extract_scholarship_links(self, soup):
        """Extract scholarship links from a page"""
        links = []
        selectors = [
            "article a[href]", "a[href*='scholarship']",
            "a[href*='grant']", "a[href*='award']", "a[href*='fellowship']",
            ".post a[href]", ".entry a[href]", ".card a[href]", ".box a[href]"
        ]

        processed_urls = set()

        for sel in selectors:
            for a in soup.select(sel):
                href = a.get("href")
                text = a.get_text(strip=True)
                if not href or not text:
                    continue
                full_url = urljoin(self.base_url, href)
                if full_url in processed_urls:
                    continue
                if self.is_scholarship_link(href, text):
                    links.append({"title": text, "url": full_url})
                    processed_urls.add(full_url)

        return links

    def is_scholarship_link(self, href, text):
        """Determine if a link is likely a scholarship link"""
        url_keywords = ["scholarship", "grant", "award", "fellowship", "bursary", "funding"]
        text_keywords = ["scholarship", "grant", "award", "fellowship", "bursary", "funding", "opportunity"]
        exclude_keywords = ["contact", "about", "home", "login", "register", "privacy", "terms", "cookie",
                            "sitemap", "rss", "feed", "category", "tag", "author", "archive", "search",
                            "facebook", "twitter", "instagram", "linkedin", "youtube", "whatsapp", "telegram"]

        url_lower = href.lower()
        text_lower = text.lower()
        has_keyword = any(k in url_lower for k in url_keywords) or any(k in text_lower for k in text_keywords)
        not_excluded = not any(k in url_lower or k in text_lower for k in exclude_keywords)
        valid_length = 10 < len(text) < 200
        not_numbers = not text.isdigit()

        return has_keyword and not_excluded and valid_length and not_numbers

    def find_next_page(self, soup):
        """Detect 'Next' page link"""
        selectors = ["a.next", "a[rel='next']", ".pagination .next a", ".page-numbers.next a"]
        for sel in selectors:
            el = soup.select_one(sel)
            if el and el.get("href"):
                return el["href"]
        # Fallback: search for link text 'Next'
        for a in soup.find_all("a", string=re.compile(r"next", re.I)):
            if a.get("href"):
                return a["href"]
        return None


import time
from datetime import datetime

class ScholarshipBatchProcessor:
    def __init__(self):
        """
        Initialize with a detailed scholarship scraper function.
        `detail_scraper_func` should take a URL and return scholarship details as a dict.
        """
        detail_scraper = ScholarshipScraper()
        self.detail_scraper_func = detail_scraper.scrape_scholarship
        self.list_scraper = ScholarshipListScraper()

    def process_scholarship_list(self, list_url, max_scholarships=None, delay_between_scrapes=2):
        """
        Complete pipeline:
        1. Scrape scholarship URLs from list page
        2. Scrape each scholarship page for details
        Returns a structured dictionary with batch metadata and scholarships.
        """
        print(f"Starting batch scraping for: {list_url}")
        scholarships_links = self.list_scraper.scrape_scholarship_list(list_url, max_scholarships)

        if not scholarships_links:
            print("No scholarship links found!")
            return self._create_empty_batch_result(list_url)

        detailed_scholarships = []
        success_count = 0
        fail_count = 0

        for idx, sch in enumerate(scholarships_links, start=1):
            print(f"Processing {idx}/{len(scholarships_links)}: {sch['title'][:50]}...")
            try:
                details = self.detail_scraper_func(sch['url'])
                if details:
                    scholarship_name = details.get('title', sch['title']) or f"Scholarship_{idx}"
                    detailed_scholarships.append({
                        'name': scholarship_name,
                        'source_info': {
                            'list_title': sch['title'],
                            'source_url': sch['url'],
                            'scraped_at': datetime.now().isoformat()
                        },
                        'scholarship_data': details,
                        'additional_list_info': {k: v for k, v in sch.items() if k not in ['title', 'url']}
                    })
                    success_count += 1
                    print("✓ Successfully scraped")
                else:
                    fail_count += 1
                    print("✗ Failed: No data returned")
            except Exception as e:
                fail_count += 1
                print(f"✗ Error scraping {sch['url']}: {e}")

            if idx < len(scholarships_links):
                time.sleep(delay_between_scrapes)

        return self._create_batch_result(list_url, detailed_scholarships, len(scholarships_links), success_count, fail_count)

    def _create_batch_result(self, source_url, scholarships, total_found, success, fail):
        """Return structured batch result"""
        return {
            'batch_metadata': {
                'batch_id': f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'source_url': source_url,
                'processed_at': datetime.now().isoformat(),
                'scraper_version': '2.0',
                'processing_stats': {
                    'total_scholarships_found': total_found,
                    'successful_scrapes': success,
                    'failed_scrapes': fail,
                    'success_rate': f"{(success / total_found * 100):.1f}%" if total_found else "0%"
                }
            },
            'scholarships': {s['name']: s for s in scholarships},
            'summary': {
                'total_scholarships': len(scholarships),
                'scholarship_names': [s['name'] for s in scholarships],
                'available_fields': self._get_available_fields(scholarships) if scholarships else []
            }
        }

    def _create_empty_batch_result(self, source_url):
        """Return empty batch result when no scholarships found"""
        return self._create_batch_result(source_url, [], 0, 0, 0)

    def _get_available_fields(self, scholarships):
        """Get all unique fields present in scholarship_data"""
        fields = set()
        for s in scholarships:
            if 'scholarship_data' in s and isinstance(s['scholarship_data'], dict):
                fields.update(s['scholarship_data'].keys())
        return sorted(fields)


# def main_scholarship_scraper(list_url, max_scholarships=5, delay_between_scrapes=2, detail_scraper_func=None):
#     if not detail_scraper_func:
#         raise ValueError("A detail_scraper_func must be provided!")

#     processor = ScholarshipBatchProcessor(detail_scraper_func)
#     start_time = datetime.now()
#     results = processor.process_scholarship_list(list_url, max_scholarships, delay_between_scrapes)
#     end_time = datetime.now()
#     print(f"Batch completed in {end_time - start_time}")
#     return results

def main_scholarship_scraper(list_url, max_scholarships=5, delay_between_scrapes=3):
    """
    Complete scholarship scraping pipeline that:
    1. Scrapes the list of scholarship URLs
    2. Scrapes detailed info from each scholarship page
    3. Returns a nested dictionary with batch metadata and scholarship data
    """
    try:
        # Initialize the detailed scraper and list scraper inside
        batch_processor = ScholarshipBatchProcessor()
        
        # Start timing
        start_time = datetime.now()
        
        # Step 1 & 2: Process the scholarship list and scrape details internally
        results = batch_processor.process_scholarship_list(
            list_url=list_url,
            max_scholarships=max_scholarships,
            delay_between_scrapes=delay_between_scrapes
        )
        
        end_time = datetime.now()
        processing_time = end_time - start_time
        print(f"Total processing time: {processing_time}")
        
        return results
        
    except Exception as e:
        print(f"Error in scraping pipeline: {str(e)}")
        return None
