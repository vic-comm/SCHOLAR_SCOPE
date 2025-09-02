
import json
from typing import List
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, CrawlResult
from crawl4ai import JsonCssExtractionStrategy, LLMExtractionStrategy
from crawl4ai import LLMConfig
from crawl4ai import BrowserConfig
import re
import json
import time
from typing import List, Dict
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CrawlResult

async def scholarship_extractor(url: str):
    """Scrape scholarship-like data from a webpage using LLM extraction."""

    # Build an extraction strategy for scholarships
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="groq/llama3-8b-8192",
            api_token="env:GROQ_API_KEY",
        ),
        instruction=(
            "Extract scholarship information from the webpage if available. "
            "If the page is not about a scholarship, return {not_a_scholarship: true}. "
            "Fields to extract (if applicable): "
            "title, description, reward, link, start_date, end_date, "
            "requirements, eligibility, tags, level."
        ),
        extract_type="schema",
        schema=json.dumps({
            "title": "string",
            "description": "string",
            "reward": "string",
            "link": "string",
            "start_date": "string",
            "end_date": "string",
            "requirements": "list[string]",
            "eligibility": "list[string]",
            "tags": "list[string]",
            "level": "list[string]",
            "not_a_scholarship": "bool"
        }),
        extra_args={
            "temperature": 0.0,
            "max_tokens": 4096,
        },
        verbose=True,
    )

    config = CrawlerRunConfig(extraction_strategy=extraction_strategy)

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(url, config=config)

        extracted_data = []
        for result in results:
            if result.success:
                try:
                    data = json.loads(result.extracted_content)
                except json.JSONDecodeError:
                    data = {"error": "Invalid extraction format"}
            else:
                data = {"error": "Failed to extract data"}

            extracted_data.append({
                "url": result.url,
                "success": result.success,
                "data": data
            })

        return extracted_data


# Example usage:
# results = await scholarship_extractor("https://example.com/scholarship-page")
# print(results)
def is_scholarship_link(href: str, text: str) -> bool:
    """Determine if a link is likely a scholarship link"""
    url_keywords = ["scholarship", "grant", "award", "fellowship", "bursary", "funding"]
    text_keywords = url_keywords + ["opportunity"]

    exclude_keywords = [
        "contact", "about", "home", "login", "register", "privacy",
        "terms", "cookie", "sitemap", "rss", "feed", "category",
        "tag", "author", "archive", "search", "facebook", "twitter",
        "instagram", "linkedin", "youtube", "whatsapp", "telegram"
    ]

    url_lower, text_lower = href.lower(), text.lower()

    has_scholarship_keyword = (
        any(k in url_lower for k in url_keywords) or
        any(k in text_lower for k in text_keywords)
    )
    not_excluded = not any(k in url_lower or k in text_lower for k in exclude_keywords)


    return has_scholarship_keyword and not_excluded

def get_next_page_url(links: List[Dict], base_url: str) -> str | None:
    """Find the next page link from extracted links"""
    next_keywords = ["next", "older", "›", "»"]
    for link in links:
        text = link.get("text", "").strip().lower()
        href = link.get("href")
        if not href:
            continue

        if any(k in text for k in next_keywords):
            return urljoin(base_url, href)

    return None

async def scholarship_list_scraper(list_url: str, max_scholarships: int = None) -> List[Dict]:
    """
    Crawl a scholarship listing page and extract scholarship links.
    Handles pagination and basic filtering (like ScholarshipListScraper).
    """
    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig()
        all_scholarship_links = []
        processed_urls = set()
        page_num = 1
        current_url = list_url

        while True:
            print(f"Scraping scholarship list page {page_num}: {current_url}")
            results: List[CrawlResult] = await crawler.arun(current_url, config=config)
            # print(results)

            if not results:
                print("No crawl results.")
                break

            result = results[0]
            if not result.success:
                print(f"Failed to scrape {current_url}")
                break

            # Extract internal + external links
            links = result.links.get("internal", []) + result.links.get("external", [])
            print(f"Found {len(links)} links on page {page_num}")
            print(links)

            page_links = []

            for link in links:
                href = link.get("href")
                text = link.get("text", "").strip()
                if not href:
                    continue

                full_url = urljoin(current_url, href)

                if full_url in processed_urls:
                    continue

                if is_scholarship_link(href, text):
                    scholarship_info = {
                        "title": text,
                        "url": full_url,
                        "extracted_from": "crawl4ai"
                    }
                    page_links.append(scholarship_info)
                    processed_urls.add(full_url)

            if not page_links:
                print("No scholarship links found on this page.")
                break

            all_scholarship_links.extend(page_links)
            print(f"Extracted {len(page_links)} scholarships from page {page_num}")

            # Check max limit
            if max_scholarships and len(all_scholarship_links) >= max_scholarships:
                all_scholarship_links = all_scholarship_links[:max_scholarships]
                print(f"Reached maximum of {max_scholarships} scholarships.")
                break

            # Try to find next page
            next_page_url = get_next_page_url(links, current_url)
            if not next_page_url:
                print("No more pages available.")
                break

            current_url = next_page_url
            page_num += 1
            time.sleep(2)  # polite crawling

        print(f"Total scholarships found: {len(all_scholarship_links)}")
        return all_scholarship_links




async def scrape_and_extract(list_url: str, max_scholarships: int = 5) -> List[Dict]:
    scholarship_links = await scholarship_list_scraper(list_url, max_scholarships)
    results = []

    for s in scholarship_links:
        print(f"Extracting from {s['url']}")
        data = await scholarship_extractor(s["url"])
        results.append(data)

    return results

import re
from datetime import datetime
from crawl4ai import CrawlResult
import os
import json
import re
from datetime import datetime
from urllib.parse import urljoin
from difflib import get_close_matches
from typing import List

from crawl4ai import AsyncWebCrawler, CrawlResult, CrawlerRunConfig, JsonCssExtractionStrategy, BrowserConfig

class ScholarshipCrawl4AIScraper:
    def __init__(self, headless=True):
        self.headless = headless

    async def scrape(self, url: str) -> dict:
        """Scrape a single scholarship URL and return structured data"""
        # Define a general schema to extract common fields
        schema = {
            "name": "scholarship",
            "baseSelector": "body",
            "fields": [
                {"name": "title", "selector": "h1, .scholarship-title, [class*='title']", "type": "text"},
                {"name": "description", "selector": "p, .entry-content, .post-content, article", "type": "text"},
                {"name": "reward", "selector": "body", "type": "text"},
                {"name": "link", "selector": "a[href*='apply'], button[onclick*='apply']", "type": "href"},
                {"name": "start_date", "selector": "body", "type": "text"},
                {"name": "end_date", "selector": "body", "type": "text"},
                {"name": "requirements", "selector": "ul li, ol li, .requirements li", "type": "text"},
                {"name": "eligibility", "selector": "ul li, ol li, .eligibility li", "type": "text"},
                {"name": "tags", "selector": "meta[name='keywords'], .tags a, .categories a", "type": "text"},
                {"name": "level", "selector": "body", "type": "text"},
            ],
        }

        extraction_strategy = JsonCssExtractionStrategy(schema)

        async with AsyncWebCrawler(config=BrowserConfig(headless=self.headless)) as crawler:
            results: List[CrawlResult] = await crawler.arun(
                url=url,
                config=CrawlerRunConfig(extraction_strategy=extraction_strategy)
            )

        if not results or not results[0].success:
            print(f"Failed to scrape {url}")
            return {}

        raw_data = json.loads(results[0].extracted_content)
        if isinstance(raw_data, list) and len(raw_data) > 0:
            raw_data = raw_data[0]  # now raw_data is a dict

        # Post-process to clean and normalize fields
        return {
            "title": self._extract_title(raw_data),
            "description": self._extract_description(raw_data),
            "reward": self._extract_reward(raw_data),
            "link": self._extract_application_link(raw_data, url),
            "start_date": self._extract_date(raw_data.get("start_date")),
            "end_date": self._extract_date(raw_data.get("end_date")),
            "requirements": self._extract_list(raw_data.get("requirements")),
            "eligibility": self._extract_list(raw_data.get("eligibility")),
            "tags": self._extract_tags(raw_data.get("tags")),
            "level": self._extract_levels(raw_data.get("level")),
            "scraped_at": datetime.now().isoformat(),
        }

    def _extract_title(self, data):
        title = data.get("title", "")
        if title:
            title = re.split(r'\||-', title)[0].strip()
        return title or "Title not found"

    def _extract_description(self, data):
        desc = data.get("description", "")
        if isinstance(desc, list):
            desc = " ".join(desc)
        return re.sub(r'\s+', ' ', desc).strip()[:1000] or "Description not available"

    def _extract_reward(self, data):
        text = data.get("reward", "").lower()
        patterns = [
            r'₦\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'\$\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'amount\s*(?:of\s*)?₦?\$?\s*([0-9,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                value = match.group(1)
                if "₦" in pattern:
                    return f"₦{value}"
                return f"${value}"
        return "Amount not specified"

    def _extract_application_link(self, data, base_url):
        link = data.get("link")
        if isinstance(link, list):
            link = link[0]
        if not link:
            return {"text": "Application link not found", "url": ""}
        href = link if isinstance(link, str) else link.get("href") or link.get("url")
        return {"text": "Apply", "url": urljoin(base_url, href)}

    def _extract_date(self, text):
        if not text:
            return None
        text = text.strip()
        date_formats = [
            "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d",
            "%d-%m-%Y", "%B %d, %Y", "%d %B %Y",
            "%b %d, %Y", "%d %b %Y", "%Y/%m/%d"
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(text, fmt).isoformat()
            except:
                continue
        return None

    def _extract_list(self, data):
        if not data:
            return []
        if isinstance(data, str):
            return [line.strip() for line in re.split(r'\n|;|•|►|→|➤', data) if line.strip()]
        if isinstance(data, list):
            return [line.strip() for line in data if line.strip()]
        return []

    def _extract_tags(self, data):
        tag_map = {'international': 'International', 'merit': 'Merit', 'need': 'Need', 'general': 'General'}
        tags = []
        if isinstance(data, str):
            data = [data]
        for item in data or []:
            item = item.lower()
            for key in tag_map:
                if key in item:
                    tags.append(tag_map[key])
        return tags or ["General"]

    def _extract_levels(self, text):
        level_map = {
            "highschool": "High School",
            "undergraduate": "Undergraduate",
            "postgraduate": "Postgraduate",
            "phd": "PhD",
            "other": "Other"
        }
        levels = []
        if text:
            text = text.lower()
            for key in level_map:
                if key in text:
                    levels.append(level_map[key])
        return levels or ["Other"]
import asyncio
results = asyncio.run(scholarship_list_scraper("https://www.scholarshipregion.com/category/undergraduate-scholarships/"))
print(results)

# scraper = ScholarshipCrawl4AIScraper()
# single_result = asyncio.run(scraper.scrape(url = "https://www.scholarshipregion.com/qatar-airways-university-scholarship"))
# print(single_result)

