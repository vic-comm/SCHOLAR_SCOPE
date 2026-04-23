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
        
        for url in self.start_urls:
            list_domain = urlparse(url).netloc.replace("www.", "")
            if list_domain not in self.allowed_domains:
                self.allowed_domains.extend([list_domain, f"www.{list_domain}"])

        self.logger.debug(f"Allowed domains: {self.allowed_domains}")

        self.existing_fingerprints = set(
            Scholarship.objects.values_list("fingerprint", flat=True)
        )
        self.llm_engine = LLMEngine()

    # ── list page ─────────────────────────────────────────────────────────────

    def start_requests(self):
        self.logger.error("🔥 start_requests CALLED 🔥")
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
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
                
    async def parse_list(self, response):
        if response.status == 403:
            self.logger.warning(f"Blocked (403) — skipping: {response.url}")
            return
        if response.status == 202:
            self.logger.warning(f"Got 202 (still processing) — page may not be fully rendered: {response.url}")

        cfg = self.site_config
        current_page = response.meta.get("page_number", 1)
        MAX_PAGES = 2

        link_sel_raw  = cfg.link_selector.replace("::attr(href)", "").strip()
        title_sel_raw = cfg.title_selector.replace("::text", "").strip()

        for card in response.css(cfg.list_item_selector):
            if self.scraped_count >= self.max_items:
                self.logger.info(f"Reached max ({self.max_items}) for {cfg.name}")
                break
            if self.consecutive_duplicates >= 3:
                self.logger.info("⚠ Stopping: 3 consecutive duplicates")
                break

            # Extract href
            relative_link = (
                card.css(link_sel_raw).attrib.get("href")
                or card.css(link_sel_raw).xpath("@href").get()
            )
            if not relative_link:
                self.logger.warning(f"No link with selector: {link_sel_raw}")
                continue

            # Extract title
            title = (
                card.css(f"{title_sel_raw}::text").get()
                or card.css(title_sel_raw).xpath("string(.)").get()
            )
            if not title:
                continue

            url = response.urljoin(relative_link)
            fingerprint = generate_fingerprint(title, url)

            if fingerprint in self.existing_fingerprints:
                self.consecutive_duplicates += 1
                self.logger.info(f"⚠ Duplicate #{self.consecutive_duplicates}/3: {title}")
                continue

            self.consecutive_duplicates = 0
            self.existing_fingerprints.add(fingerprint)
            self.scraped_count += 1

            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "fingerprint": fingerprint,
                    "title": title,
                    "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded", "timeout": 60_000},
                },
                callback=self.parse_detail,
            )

        # Pagination
        if current_page < MAX_PAGES and self.consecutive_duplicates < 3:
            next_page = (
                response.css("a.next::attr(href)").get()
                or response.css("a.next.page-numbers::attr(href)").get()
                or response.css('a[rel="next"]::attr(href)').get()
                or response.css(".pagination a.active + a::attr(href)").get()
            )
            if next_page:
                yield scrapy.Request(
                    response.urljoin(next_page),
                    callback=self.parse_list,
                    meta={
                        "playwright": True,
                        "playwright_page_goto_kwargs": {"wait_until": "networkidle", "timeout": 90_000},
                        "page_number": current_page + 1,
                    },
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
            recovered = await self.llm_engine.extract_data(response.text, response.url)
            if isinstance(recovered, list):
                recovered = recovered[0] if recovered else {}
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
