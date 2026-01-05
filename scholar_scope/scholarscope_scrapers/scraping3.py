from datetime import datetime
import re
from urllib.parse import urljoin
from difflib import get_close_matches
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup
from hashlib import sha256
import time

class ScholarshipScraper:
    def __init__(self, site_config, chrome_driver_path=None):
        self.site_config = site_config
        self.driver = None
        self.chrome_driver_path = chrome_driver_path

    def connect_browser(self):
        options = ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        if self.chrome_driver_path:
            service = Service(self.chrome_driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def scrape(self, url):
        self.connect_browser()
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        data = {
            "title": self.extract_title(),
            "description": self.extract_description(),
            "link": self.extract_application_link(),
            "reward": self.extract_reward(),
            "start_date": self.extract_start_date(),
            "end_date": self.extract_end_date(),
            "requirements": self.extract_requirements(),
            "eligibility": self.extract_eligibility(),
            "levels": self.extract_levels(),
            "tags": self.extract_tags(),
            "scraped_at": datetime.now()
        }
        self.driver.quit()
        return data

    # --- Title & description ---
    def extract_title(self):
        cfg = self.site_config
        if cfg.title_selector:
            elems = self.driver.find_elements(By.CSS_SELECTOR, cfg.title_selector)
            if elems:
                return elems[0].text.strip()[:255]
        return self.driver.title.split('|')[0].strip()[:255]

    def extract_description(self):
        cfg = self.site_config
        text = ""
        if cfg.description_selector:
            text = " ".join([el.text for el in self.driver.find_elements(By.CSS_SELECTOR, cfg.description_selector + " *")])
        if not text:
            paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "p")
            text = " ".join(p.text for p in paragraphs[:5])
        return re.sub(r'\s+', ' ', text).strip() or "No description available"

    # --- Application link ---
    def extract_application_link(self):
        cfg = self.site_config
        if cfg.link_selector:
            elems = self.driver.find_elements(By.CSS_SELECTOR, cfg.link_selector)
            if elems:
                href = elems[0].get_attribute("href") or elems[0].get_attribute("onclick")
                if href:
                    return self._normalize_url(href)
        # fallback to heuristics
        return self.driver.current_url

    def _normalize_url(self, link):
        if not link:
            return ""
        if "window.location" in link:
            match = re.search(r"['\"](http.*?|/.*?|.*?\.php.*?)['\"]", link)
            if match:
                link = match.group(1)
        return urljoin(self.driver.current_url, link)

    # --- Rewards, dates ---
    def extract_reward(self):
        text = self.driver.find_element(By.TAG_NAME, "body").text
        patterns = [r'₦\s*([0-9,]+)', r'\$\s*([0-9,]+)']
        for p in patterns:
            m = re.findall(p, text)
            if m:
                return m[0]
        return "Amount not specified"

    def parse_date_string(self, date_str):
        date_str = re.sub(r'^(on|by|from|until|before|after)\s+', '', date_str, flags=re.I)
        date_str = re.sub(r'\s+(onwards?|forward)$', '', date_str, flags=re.I)
        formats = ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%B %d, %Y', '%d %B %Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        return None

    def extract_start_date(self):
        text = self.driver.find_element(By.TAG_NAME, "body").text
        matches = re.findall(r'(?:start|open|begin).*?[:\s]*([^\n.]+)', text, re.I)
        if matches:
            return self.parse_date_string(matches[0].strip())
        return None

    def extract_end_date(self):
        text = self.driver.find_element(By.TAG_NAME, "body").text
        matches = re.findall(r'(?:deadline|due|close).*?[:\s]*([^\n.]+)', text, re.I)
        if matches:
            return self.parse_date_string(matches[0].strip())
        return None

    # --- Requirements & eligibility ---
    def extract_requirements(self):
        cfg = self.site_config
        if cfg.requirements_selector:
            elements = self.driver.find_elements(By.CSS_SELECTOR, cfg.requirements_selector + " *")
            text = " ".join([el.text for el in elements])
        else:
            text = self.driver.find_element(By.TAG_NAME, "body").text
        return self._extract_list_items(text, requirement=True)

    def extract_eligibility(self):
        cfg = self.site_config
        if cfg.eligibility_selector:
            elements = self.driver.find_elements(By.CSS_SELECTOR, cfg.eligibility_selector + " *")
            text = " ".join([el.text for el in elements])
        else:
            text = self.driver.find_element(By.TAG_NAME, "body").text
        return self._extract_list_items(text, requirement=False)

    def _extract_list_items(self, text, requirement=True):
        items = []
        patterns = [r'[\n;•►→➤]', r'[.!?]']
        for p in patterns:
            parts = re.split(p, text)
            for part in parts:
                part = part.strip()
                if requirement and self.is_requirement_text(part):
                    items.append(part)
                elif not requirement and self.is_eligibility_text(part):
                    items.append(part)
        return list(dict.fromkeys(items))[:10] or ["Not specified"]

    def is_requirement_text(self, text):
        keywords = ['transcript', 'certificate', 'cv', 'resume', 'letter', 'essay', 'statement', 'passport', 'photo', 'application form']
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 200

    def is_eligibility_text(self, text):
        keywords = ['citizen', 'age', 'undergraduate', 'graduate', 'student', 'female', 'male']
        t = text.lower()
        return any(k in t for k in keywords) and 15 < len(text) < 200

    # --- Levels & tags ---
    def extract_levels(self):
        cfg = self.site_config
        if cfg.level_selector:
            elems = self.driver.find_elements(By.CSS_SELECTOR, cfg.level_selector)
            levels = [el.text.lower() for el in elems if el.text.strip()]
            if levels:
                return levels
        # fallback heuristic
        text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        keywords = {"highschool":["high school","secondary"],"undergraduate":["undergraduate","bachelor"],"postgraduate":["postgraduate","master"],"phd":["phd","doctorate"]}
        detected = [lvl for lvl, keys in keywords.items() if any(k in text for k in keys)]
        return detected or ["unspecified"]

    def extract_tags(self):
        cfg = self.site_config
        if cfg.tag_selector:
            elems = self.driver.find_elements(By.CSS_SELECTOR, cfg.tag_selector)
            tags = [el.text.lower() for el in elems if el.text.strip()]
            if tags:
                return tags
        # fallback heuristic
        text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        tag_keywords = {"international":["international","abroad"],"women":["female","women"],"stem":["stem","science"],"merit":["merit"],"need":["need","financial"]}
        detected = [tag for tag, keys in tag_keywords.items() if any(k in text for k in keys)]
        return detected or ["general"]

def generate_fingerprint(title, url):
    return sha256(f"{title}|{url}".encode("utf-8")).hexdigest()


class ScholarshipListScraper:
    def __init__(self, site_config, max_items=50, delay=2):
        """
        site_config: instance of SiteConfig
        max_items: maximum scholarships to scrape
        delay: seconds to wait between page requests
        """
        self.site_config = site_config
        self.max_items = max_items
        self.scraped_count = 0
        self.consecutive_duplicates = 0
        self.existing_fingerprints = set()
        self.delay = delay

    def scrape_list(self):
        list_url = self.site_config.list_url
        all_items = []

        while list_url:
            try:
                response = requests.get(list_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
            except Exception as e:
                print(f"Error fetching {list_url}: {e}")
                break

            items = self.parse_list(soup, list_url)
            all_items.extend(items)

            if self.scraped_count >= self.max_items or self.consecutive_duplicates >= 3:
                break

            next_page_url = self.find_next_page(soup, list_url)
            if not next_page_url:
                break

            list_url = next_page_url
            time.sleep(self.delay)

        print(f"Total scholarships scraped: {len(all_items)}")
        return all_items

    def parse_list(self, soup, base_url):
        cfg = self.site_config
        list_item_sel = cfg.list_item_selector
        link_sel = cfg.link_selector
        title_sel = cfg.title_selector

        scraped_items = []

        for card in soup.select(list_item_sel):
            if self.scraped_count >= self.max_items:
                break

            if self.consecutive_duplicates >= 3:
                break

            link_tag = card.select_one(link_sel)
            title_tag = card.select_one(title_sel)

            if not link_tag or not title_tag:
                continue

            relative_link = link_tag.get("href")
            title = title_tag.get_text(strip=True)
            if not relative_link or not title:
                continue

            url = urljoin(base_url, relative_link)
            fingerprint = generate_fingerprint(title, url)

            if fingerprint in self.existing_fingerprints:
                self.consecutive_duplicates += 1
                print(f"Duplicate #{self.consecutive_duplicates}/3: {title}")
                continue
            else:
                self.consecutive_duplicates = 0
                self.existing_fingerprints.add(fingerprint)

            self.scraped_count += 1

            scraped_items.append({
                "title": title,
                "url": url,
                "fingerprint": fingerprint
            })

        return scraped_items

    def find_next_page(self, soup, current_url):
        """
        Attempt to find a next page link.
        Tries common patterns: rel="next", next-page class, pagination links containing "next".
        """
        # 1. rel="next"
        next_link = soup.find("a", rel="next")
        if next_link and next_link.get("href"):
            return urljoin(current_url, next_link["href"])

        # 2. common CSS selectors
        selectors = [
            ".next-page a",
            ".pagination .next a",
            ".page-numbers.next",
            ".wp-pagenavi .next a"
        ]
        for sel in selectors:
            tag = soup.select_one(sel)
            if tag and tag.get("href"):
                return urljoin(current_url, tag["href"])

        # 3. link text containing 'next'
        for a in soup.find_all("a", string=re.compile(r"next|>", re.I)):
            if a.get("href"):
                return urljoin(current_url, a["href"])

        return None


class ScholarshipBatchProcessor:
    def __init__(self, site_config, max_items=50, delay_between_scrapes=2):
        self.site_config = site_config
        self.list_scraper = ScholarshipListScraper(site_config, max_items=max_items, delay=delay_between_scrapes)
        self.detail_scraper = ScholarshipScraper(site_config)
        self.delay = delay_between_scrapes

    def process_site(self):
        """
        Scrape all scholarships for the site_config.
        Returns list of scraped scholarship dictionaries, ready for bulk_create.
        """
        print(f"Starting batch scrape for {self.site_config.name}")
        scraped_scholarships = []

        # Step 1: Get all scholarship URLs
        try:
            urls = self.list_scraper.scrape_list()
            if not urls:
                print("No scholarships found on the list page.")
                return []
        except Exception as e:
            print(f"Error scraping list page: {e}")
            return []

        print(f"Found {len(urls)} scholarships. Starting detail scrape...")

        # Step 2: Scrape each scholarship individually
        for i, item in enumerate(urls, 1):
            url = item.get("url")
            title = item.get("title")
            print(f"[{i}/{len(urls)}] Scraping: {title} ({url})")
            try:
                details = self.detail_scraper.scrape(url)
                if not details:
                    print(f"⚠ No details returned for {title}")
                    continue

                # Add fingerprint and scraped_at if missing
                if "fingerprint" not in details:
                    details["fingerprint"] = generate_fingerprint(details.get("title", title), url)
                if "scraped_at" not in details:
                    details["scraped_at"] = datetime.now()

                scraped_scholarships.append({
                    "scholarship_data": details,
                    "source_info": {
                        "list_title": title,
                        "source_url": url
                    }
                })

            except Exception as e:
                print(f"✗ Failed to scrape {title}: {e}")

            time.sleep(self.delay)

        print(f"Completed scraping {len(scraped_scholarships)} scholarships for {self.site_config.name}")
        return scraped_scholarships

    # def save_batch(self, scraped_scholarships, scrape_event=None):
    #     """
    #     Save the scraped scholarships using bulk_create.
    #     """
    #     if not scraped_scholarships:
    #         print("No scholarships to save.")
    #         return 0

    #     # Map to expected dict format for bulk_create: title -> entry
    #     scholarships_dict = {}
    #     for entry in scraped_scholarships:
    #         data = entry.get("scholarship_data", {})
    #         title = data.get("title") or f"Scholarship_{len(scholarships_dict)+1}"
    #         scholarships_dict[title] = entry

    #     created_count = bulk_create(
    #         scraped_scholarships=scholarships_dict,
    #         source_name=self.site_config.name,
    #         source_url=self.site_config.list_url,
    #         scrape_event=scrape_event
    #     )
    #     return created_count
