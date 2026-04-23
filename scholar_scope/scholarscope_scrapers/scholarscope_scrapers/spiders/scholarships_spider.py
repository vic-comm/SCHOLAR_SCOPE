import scrapy
from datetime import datetime
import dateparser
from ..utils.django_setup import setup_django
from ..utils.llm_engine import LLMEngine
from ..utils.quality import QualityCheck
from .schemas import ScholarshipScrapedSchema
from pydantic import ValidationError
setup_django()
from scholarships.models import SiteConfig, Scholarship
from scholarships.utils import generate_fingerprint
from scholarships.utils import ScholarshipExtractor
from scrapy_playwright.page import PageMethod
import json
from playwright_stealth import stealth_async
import os

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

def should_abort_request(request):
    """
    Blocks images, fonts, and ad domains to speed up scraping.
    """
    # 1. Block Resource Types
    if request.resource_type in ["image", "media", "font", "stylesheet"]:
        return True
        
    # 2. Block Ad Domains
    url = request.url.lower()
    ad_domains = [
        "googleads", "doubleclick", "googlesyndication", "facebook", 
        "twitter", "linkedin", "analytics", "tracking", "temu", 
        "quantserve", "criteo", "outbrain", "taboola"
    ]
    if any(domain in url for domain in ad_domains):
        return True
        
    return False

def build_scraperapi_url(target_url: str) -> str:
    """Wrap a target URL for ScraperAPI with JS rendering enabled."""
    return (
        f"http://api.scraperapi.com/"
        f"?api_key={SCRAPERAPI_KEY}"
        f"&url={target_url}"
        f"&render=true"          # JavaScript rendering
        f"&country_code=us"      
        f"&keep_headers=false"
    )

class ScholarshipBatchSpider(scrapy.Spider):
    name = "scholarship_batch"
    custom_settings = {
        "ITEM_PIPELINES": {
            "scholarscope_scrapers.scholarscope_scrapers.pipelines.RenewalAndDuplicatePipeline": 200,
            "scholarscope_scrapers.scholarscope_scrapers.pipelines.ScholarshipPipeline": 300,
        },
        "PLAYWRIGHT_ABORT_REQUEST": should_abort_request,
        "DOWNLOAD_HANDLERS": {
            "http":  "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_BROWSER_TYPE": "firefox",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True, "timeout": 60_000},
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
        "DOWNLOAD_TIMEOUT": 90,
    }

    # ── init ──────────────────────────────────────────────────────────────────

    def __init__(self, site_config_id=None, scrape_event_id=None, max_items=30, **kwargs):
        super().__init__(**kwargs)

        if not site_config_id:
            raise ValueError("site_config_id is required!")

        self.site_config = SiteConfig.objects.get(id=site_config_id)
        from scholarships.models import ListingSource
        self.sources = ListingSource.objects.filter(site=self.site_config, active=True)
        self.start_urls = [source.url for source in self.sources]
        self.scrape_event_id = scrape_event_id
        self.max_items = int(max_items)
        self.scraped_count = 0
        self.consecutive_duplicates = 0

        from urllib.parse import urlparse

        parsed_base = urlparse(self.site_config.base_url)
        clean_domain = parsed_base.netloc.replace("www.", "")
        self.allowed_domains = [clean_domain, f"www.{clean_domain}"]
        
        self.using_scraperapi = bool(SCRAPERAPI_KEY)
        self.scraperapi_failed = False  # flips to True on quota exhaustion

        for url in self.start_urls:
            list_domain = urlparse(url).netloc.replace("www.", "")
            if list_domain not in self.allowed_domains:
                self.allowed_domains.extend([list_domain, f"www.{list_domain}"])

        self.logger.debug(f"Allowed domains: {self.allowed_domains}")

        self.existing_fingerprints = set(
            Scholarship.objects.values_list("fingerprint", flat=True)
        )
        self.llm_engine = LLMEngine()

    def _make_scraperapi_request(self, url, callback, **meta_extras):
        """
        Build a plain HTTP request through ScraperAPI.
        No Playwright involved — ScraperAPI handles the browser on their end.
        """
        api_url = build_scraperapi_url(url)
        return scrapy.Request(
            url=api_url,
            callback=callback,
            meta={
                "original_url": url,   # preserve for pagination and item links
                "via_scraperapi": True,
                **meta_extras,
            },
            dont_filter=True,  # ScraperAPI URL differs from original, bypass dupe filter
        )
    
    def _make_playwright_request(self, url, callback, **meta_extras):
        """
        Fall back to Scrapy-Playwright for direct browser rendering.
        Used when ScraperAPI key is absent or quota is exhausted.
        """
        return scrapy.Request(
            url,
            meta={
                "playwright": True,
                "playwright_page_goto_kwargs": {
                    "wait_until": "networkidle",
                    "timeout": 60_000,
                },
                "playwright_page_methods": [
                    PageMethod(
                        "wait_for_selector",
                        self.site_config.list_item_selector,
                        timeout=15_000,
                    ),
                ],
                **meta_extras,
            },
            callback=callback,
        )
    
    async def init_page(self, page, request):
        await stealth_async(page)

    def start_requests(self):
        self.logger.error("🔥 start_requests CALLED 🔥")
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_init_callback": self.init_page,
                    "playwright_page_goto_kwargs": {"wait_until": "networkidle", "timeout": 60_000},
                    "playwright_page_methods": [
                    PageMethod("wait_for_selector", "p.td-module-title a",state="attached", timeout=10000),
                ],
                },
                callback=self.parse_list,
                errback=self.errback_close_page,
            )

    async def errback_close_page(self, failure):
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        if failure.check(PlaywrightTimeoutError):
            page = failure.request.meta.get("playwright_page")
            if page:
                self.logger.warning(f"Timeout waiting for selector on {failure.request.url}. Closing page.")
                await page.close()

    # async def parse_list(self, response):
    #     if response.meta.get("via_scraperapi"):
    #         if self._is_scraperapi_quota_error(response):
    #             self.logger.warning(
    #                 "ScraperAPI quota exhausted. Switching to Playwright fallback."
    #             )
    #             self.scraperapi_failed = True
    #             # Re-request the same URL via Playwright
    #             original_url = response.meta.get("original_url", response.url)
    #             yield self._make_playwright_request(original_url, callback=self.parse_list)
    #             return
            
    #     if response.status == 403:
    #         self.logger.warning(f"Blocked (403) — skipping: {response.url}")
    #         return
    #     if response.status == 202:
    #         self.logger.warning(f"Got 202 (still processing) — page may not be fully rendered: {response.url}")

    #     cfg = self.site_config
    #     current_page = response.meta.get("page_number", 1)
    #     MAX_PAGES = 2

    #     base_url = response.meta.get("original_url", response.url)

    #     link_sel_raw  = cfg.link_selector.replace("::attr(href)", "").strip()
    #     title_sel_raw = cfg.title_selector.replace("::text", "").strip()

    #     cards_found = len(response.css(cfg.list_item_selector))
    #     self.logger.info(f"Cards found on {base_url}: {cards_found}")

    #     if cards_found == 0:
    #         self.logger.warning(
    #             f"No cards matched selector '{cfg.list_item_selector}' on {base_url}. "
    #             f"Page may still be bot-blocked."
    #         )
    #         return
        
    #     for card in response.css(cfg.list_item_selector):
    #         if self.scraped_count >= self.max_items:
    #             self.logger.info(f"Reached max ({self.max_items}) for {cfg.name}")
    #             break
    #         if self.consecutive_duplicates >= 3:
    #             self.logger.info("⚠ Stopping: 3 consecutive duplicates")
    #             break

    #         # Extract href
    #         relative_link = (
    #             card.css(link_sel_raw).attrib.get("href")
    #             or card.css(link_sel_raw).xpath("@href").get()
    #         )
    #         if not relative_link:
    #             self.logger.warning(f"No link with selector: {link_sel_raw}")
    #             continue

    #         # Extract title
    #         title = (
    #             card.css(f"{title_sel_raw}::text").get()
    #             or card.css(title_sel_raw).xpath("string(.)").get()
    #         )
    #         if not title:
    #             continue

    #         from urllib.parse import urljoin
    #         url = urljoin(base_url, relative_link)
    #         fingerprint = generate_fingerprint(title, url)

    #         if fingerprint in self.existing_fingerprints:
    #             self.consecutive_duplicates += 1
    #             self.logger.info(f"⚠ Duplicate #{self.consecutive_duplicates}/3: {title}")
    #             continue

    #         self.consecutive_duplicates = 0
    #         self.existing_fingerprints.add(fingerprint)
    #         self.scraped_count += 1

    #         if self.using_scraperapi and not self.scraperapi_failed:
    #             yield self._make_scraperapi_request(
    #                 url,
    #                 callback=self.parse_detail,
    #                 fingerprint=fingerprint,
    #                 title=title,
    #             )
    #         else:
    #             yield self._make_playwright_request(
    #                 url,
    #                 callback=self.parse_detail,
    #                 fingerprint=fingerprint,
    #                 title=title,
    #             )

    #     # Pagination
    #     if current_page < MAX_PAGES and self.consecutive_duplicates < 3:
    #         next_page = (
    #             response.css("a.next::attr(href)").get()
    #             or response.css("a.next.page-numbers::attr(href)").get()
    #             or response.css('a[rel="next"]::attr(href)').get()
    #             or response.css(".pagination a.active + a::attr(href)").get()
    #         )
    #         if next_page:
    #             from urllib.parse import urljoin
    #             next_url = urljoin(base_url, next_page)
    #             if self.using_scraperapi and not self.scraperapi_failed:
    #                 yield self._make_scraperapi_request(
    #                     next_url,
    #                     callback=self.parse_list,
    #                     page_number=current_page + 1,
    #                 )
    #             else:
    #                 yield self._make_playwright_request(
    #                     next_url,
    #                     callback=self.parse_list,
    #                     page_number=current_page + 1,
    #                 )

    def start_requests(self):
        self.logger.info("start_requests called")
        for url in self.start_urls:
            if self.using_scraperapi and not self.scraperapi_failed:
                self.logger.info(f"Routing via ScraperAPI: {url}")
                yield self._make_scraperapi_request(url, callback=self.parse_list)
            else:
                self.logger.info(f"Routing via Playwright: {url}")
                yield self._make_playwright_request(url, callback=self.parse_list)

    # ── List page parser ───────────────────────────────────────────────────────

    async def parse_list(self, response):
        # ── ScraperAPI quota exhaustion detection ─────────────────────────────
        # ScraperAPI returns specific status codes and body text on quota failure
        if response.meta.get("via_scraperapi"):
            if self._is_scraperapi_quota_error(response):
                self.logger.warning(
                    "ScraperAPI quota exhausted. Switching to Playwright fallback."
                )
                self.scraperapi_failed = True
                # Re-request the same URL via Playwright
                original_url = response.meta.get("original_url", response.url)
                yield self._make_playwright_request(original_url, callback=self.parse_list)
                return

        if response.status == 403:
            self.logger.warning(f"Blocked (403) — skipping: {response.url}")
            return
        if response.status == 202:
            self.logger.warning(f"Got 202 — page still processing: {response.url}")

        cfg = self.site_config
        current_page = response.meta.get("page_number", 1)
        MAX_PAGES = 2

        # When via ScraperAPI, response.url is the api.scraperapi.com URL
        # We need the original URL for resolving relative links
        base_url = response.meta.get("original_url", response.url)

        link_sel_raw  = cfg.link_selector.replace("::attr(href)", "").strip()
        title_sel_raw = cfg.title_selector.replace("::text", "").strip()

        cards_found = len(response.css(cfg.list_item_selector))
        self.logger.info(f"Cards found on {base_url}: {cards_found}")

        if cards_found == 0:
            self.logger.warning(
                f"No cards matched selector '{cfg.list_item_selector}' on {base_url}. "
                f"Page may still be bot-blocked."
            )
            return

        for card in response.css(cfg.list_item_selector):
            if self.scraped_count >= self.max_items:
                self.logger.info(f"Reached max ({self.max_items}) for {cfg.name}")
                break
            if self.consecutive_duplicates >= 3:
                self.logger.info("Stopping: 3 consecutive duplicates")
                break

            relative_link = (
                card.css(link_sel_raw).attrib.get("href")
                or card.css(link_sel_raw).xpath("@href").get()
            )
            if not relative_link:
                self.logger.warning(f"No link found with selector: {link_sel_raw}")
                continue

            title = (
                card.css(f"{title_sel_raw}::text").get()
                or card.css(title_sel_raw).xpath("string(.)").get()
            )
            if not title:
                continue

            # Resolve relative URL against the original page URL, not ScraperAPI URL
            from urllib.parse import urljoin
            url = urljoin(base_url, relative_link)
            fingerprint = generate_fingerprint(title, url)

            if fingerprint in self.existing_fingerprints:
                self.consecutive_duplicates += 1
                self.logger.info(
                    f"Duplicate #{self.consecutive_duplicates}/3: {title}"
                )
                continue

            self.consecutive_duplicates = 0
            self.existing_fingerprints.add(fingerprint)
            self.scraped_count += 1

            # Route detail page requests through same mechanism
            if self.using_scraperapi and not self.scraperapi_failed:
                yield self._make_scraperapi_request(
                    url,
                    callback=self.parse_detail,
                    fingerprint=fingerprint,
                    title=title,
                )
            else:
                yield self._make_playwright_request(
                    url,
                    callback=self.parse_detail,
                    fingerprint=fingerprint,
                    title=title,
                )

        # ── Pagination ─────────────────────────────────────────────────────────
        if current_page < MAX_PAGES and self.consecutive_duplicates < 3:
            next_page = (
                response.css("a.next::attr(href)").get()
                or response.css("a.next.page-numbers::attr(href)").get()
                or response.css('a[rel="next"]::attr(href)').get()
                or response.css(".pagination a.active + a::attr(href)").get()
            )
            if next_page:
                from urllib.parse import urljoin
                next_url = urljoin(base_url, next_page)
                if self.using_scraperapi and not self.scraperapi_failed:
                    yield self._make_scraperapi_request(
                        next_url,
                        callback=self.parse_list,
                        page_number=current_page + 1,
                    )
                else:
                    yield self._make_playwright_request(
                        next_url,
                        callback=self.parse_list,
                        page_number=current_page + 1,
                    )
    # ── detail page ───────────────────────────────────────────────────────────

    async def parse_detail(self, response):
        cfg = self.site_config

        # ── build extractor (Scrapy response mode) ────────────────────────────
        extractor = ScholarshipExtractor(scrapy_response=response)

        item = {
            "title":       extractor.extract_title(cfg.title_selector),
            "description": extractor.extract_description(cfg.description_selector),
            "reward":      extractor.extract_reward(cfg.reward_selector),
            "link":        response.url,
            "end_date":    extractor.extract_date("end",   cfg.deadline_selector),
            "start_date":  extractor.extract_date("start", cfg.start_date_selector),
            "requirements": extractor.extract_requirements(
                css_selector=cfg.requirements_selector,
                fallback_text=extractor.clean_text,
            ),
            "eligibility": extractor.extract_eligibility(
                css_selector=cfg.eligibility_selector,
                fallback_text=extractor.clean_text,
            ),
            "tags":   extractor.extract_tags(cfg.tag_selector),
            "levels": extractor.extract_levels(cfg.level_selector),
            "scraped_at": datetime.now().isoformat(),
        }

        # ── quality check + optional LLM rescue ───────────────────────────────
        quality_report = QualityCheck.get_quality_score(
            item, ["title", "reward", "end_date", "description", "requirements", "eligibility"]
        )

        if not item.get("reward"):
            item["reward"] = "Amount not specified"

        if QualityCheck.should_full_regenerate(quality_report):
            self.logger.info(f"Full LLM extraction. Score: {quality_report['quality_score']}")
            recovered = await self.llm_engine.extract_data(response.text, item["link"])
            
            if isinstance(recovered, list):
                recovered = recovered[0] if recovered else {}
            if isinstance(recovered, str):
                try:
                    import json
                    recovered = json.loads(recovered)
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse LLM response as JSON")
                    recovered = {}
                    
            _parse_dates_inplace(recovered)
            item.update(recovered)

        elif quality_report["needs_llm"]:
            fields = list(set(
                quality_report["failed_fields"]
                + [f for f, _, _ in quality_report["low_confidence_fields"]]
            ))
            if fields:
                self.logger.info(f"Partial LLM fix for: {fields}")
                recovered = await self.llm_engine.recover_specific_fields(
                    extractor.clean_text, fields
                )
                
                if isinstance(recovered, str):
                    try:
                        import json
                        recovered = json.loads(recovered)
                    except json.JSONDecodeError:
                        self.logger.error("Failed to parse partial LLM response as JSON")
                        recovered = {}
                        
                _parse_dates_inplace(recovered)
                item.update(recovered)

        # ── defaults / guard rails ────────────────────────────────────────────
        item.setdefault("title",       f"Unknown Scholarship - {response.url}")
        item.setdefault("link",        response.url)
        item.setdefault("description", "Description unavailable.")
        item.setdefault("scraped_at",  datetime.now().isoformat())

        for field in ["requirements", "eligibility", "tags", "levels"]:
            if not item.get(field):
                item[field] = []

        try:
            yield ScholarshipScrapedSchema(**item).dict()
        except ValidationError as e:
            self.logger.warning(f"Dropping '{item.get('title')}': {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Shared helper
# ─────────────────────────────────────────────────────────────────────────────

def _parse_dates_inplace(data: dict) -> None:
    """Parse any string date values in 'end_date' / 'start_date' in-place."""
    if not isinstance(data, dict):
        return
    
    for key in ("end_date", "start_date"):
        val = data.get(key)
        if isinstance(val, str):
            dt = dateparser.parse(val)
            data[key] = dt.date() if dt else None
