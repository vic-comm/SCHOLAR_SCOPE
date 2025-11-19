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

DOWNLOADER_MIDDLEWARES = {
    "scrapy_playwright.middleware.ScrapyPlaywrightMiddleware": 800,
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
ITEM_PIPELINES = {
    'scholarscope_scrapers.pipelines.ScholarshipPipeline': 300,
}
