# scholarscope_scraper/settings.py
import os
import django
import sys

# sys.path.append(os.path.dirname(os.path.abspath('.')))
# Get the absolute path to your project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the Django project (one level up from this file) to sys.path
sys.path.append(os.path.join(BASE_DIR, '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarscope.settings')
django.setup()

BOT_NAME = "scholarscope_scrapers"

SPIDER_MODULES = ["scholarscope_scrapers.spiders"]
NEWSPIDER_MODULE = "scholarscope_scrapers.spiders"

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 1.5

# DOWNLOADER_MIDDLEWARES = {
#     "scrapy_playwright.middleware.PlaywrightMiddleware": 543,
# }
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
DOWNLOAD_HANDLERS = {
    "http":  "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
ITEM_PIPELINES = {
    'scholarscope_scrapers.pipelines.RenewalAndDuplicatePipeline': 200,
    'scholarscope_scrapers.pipelines.ScholarshipPipeline': 300,
}

# scholarscope_scrapers/scholarscope_scrapers/settings.py

# import os
# from pathlib import Path

# # ────────────────────────────────────────────────────────────────
# # DJANGO SETUP — MUST BE AT THE TOP
# # ────────────────────────────────────────────────────────────────
# BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # goes up to scholar_scope/
# import sys
# sys.path.append(str(BASE_DIR))

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarscope.scholarscope.settings')
# import django
# django.setup()
# # ────────────────────────────────────────────────────────────────

# BOT_NAME = "scholarscope_scrapers"

# SPIDER_MODULES = ["scholarscope_scrapers.spiders"]
# NEWSPIDER_MODULE = "scholarscope_scrapers.spiders"

# # ────────────────────── SCRAPY SETTINGS ──────────────────────
# ROBOTSTXT_OBEY = False
# DOWNLOAD_DELAY = 2

# # CORRECT PLAYWRIGHT MIDDLEWARE (2024+ version)
# DOWNLOADER_MIDDLEWARES = {
#     "scrapy_playwright.middleware.PlaywrightMiddleware": 543,
# }

# # Required for scrapy-playwright
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# # Playwright-specific settings
# PLAYWRIGHT_BROWSER_TYPE = "chromium"
# PLAYWRIGHT_LAUNCH_OPTIONS = {
#     "headless": True,
#     "timeout": 30000,
# }
# PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000

# # Your pipeline
# ITEM_PIPELINES = {
#     "scholarscope_scrapers.pipelines.ScholarshipPipeline": 300,
# }

# # Optional: make it faster in dev
# CONCURRENT_REQUESTS = 8
# CONCURRENT_REQUESTS_PER_DOMAIN = 4

# scholarscope_scrapers/scholarscope_scrapers/settings.py
# (Official Scrapy-Playwright config for 2025)

# import os
# from pathlib import Path

# # ────────────────────────────────────────────────────────────────
# # DJANGO SETUP — Essential for your models (SiteConfig, Scholarship)
# # ────────────────────────────────────────────────────────────────
# BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # Up to scholar_scope/ root
# import sys
# sys.path.append(str(BASE_DIR))

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarscope.settings')
# import django
# django.setup()
# # ────────────────────────────────────────────────────────────────

# # Basic Scrapy Settings
# BOT_NAME = "scholarscope_scrapers"
# SPIDER_MODULES = ["scholarscope_scrapers.spiders"]
# NEWSPIDER_MODULE = "scholarscope_scrapers.spiders"

# ROBOTSTXT_OBEY = False
# DOWNLOAD_DELAY = 2.0  # Polite scraping (adjust for production)
# CONCURRENT_REQUESTS = 8
# CONCURRENT_REQUESTS_PER_DOMAIN = 4

# # ────────────────────── SCRAPY-PLAYWRIGHT MIDDLEWARE (2025 Standard) ──────────────────────
# # CRITICAL: This is the exact name from official docs — fixes your error
# DOWNLOADER_MIDDLEWARES = {
#     "scrapy_playwright.middleware.PlaywrightMiddleware": 543,  # ← THIS LINE FIXES IT
# }

# # Playwright Settings (for JS-heavy sites like scholarship pages)
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
# PLAYWRIGHT_BROWSER_TYPE = "chromium"
# PLAYWRIGHT_LAUNCH_OPTIONS = {
#     "headless": True,  # Set to False for debugging (visible browser)
#     "timeout": 30000,
# }
# PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000  # 30s per page
# PLAYWRIGHT_ABORT_REQUEST = lambda req: req.resource_type in {"image", "stylesheet", "font"}  # Skip non-HTML for speed

# # Your Pipeline (for saving to Django DB)
# ITEM_PIPELINES = {
#     "scholarscope_scrapers.pipelines.ScholarshipPipeline": 300,
# }

# # Logging (optional: reduces noise during tests)
# LOG_LEVEL = "INFO"  # Change to "DEBUG" for verbose output
# LOG_FILE = "scrapy.log"  # Logs to file for easy review