# from celery import shared_task
# from .models import Scholarship, ScholarshipScrapeEvent, Level, Tag, SiteConfig, Profile, FailedScholarship
# from django.utils import timezone
# from django.utils.text import slugify
# from scholarships.services import ScholarshipEmailService
# from scholarships.utils import random_string_generator
# from django.core.cache import cache
# from datetime import datetime, timedelta
# from django.db import transaction
# from scholarships.utils import generate_fingerprint, get_text_embedding, _rec_cache_key
# import os
# os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'scholarscope_scrapers.settings')
# import importlib
# # from scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider import ScholarshipBatchSpider
# # from ..scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider import ScholarshipBatchSpider
# # from scholarscope_scrapers.spiders.scholarships_spider import ScholarshipBatchSpider
# import logging
# import importlib
# # import billiard as multiprocessing
# from celery import shared_task
# from django.utils import timezone
# from scrapy.crawler import CrawlerProcess
# from .models import SiteConfig
# import sys


# # def _run_spider_process(site_config_id, scrape_event_id):
# #     """
# #     This function runs in a fresh OS process.
# #     It adds the parent directory to sys.path so we can find the scraper,
# #     then launches the spider.
# #     """
# #     try:
# #         # 1. Add the project root to sys.path so we can find 'scholarscope_scrapers'
# #         # Assuming structure:
# #         # /Projects/SCHOLAR_SCOPE/scholar_scope/scholarships/tasks.py
# #         # We want to reach:   /Projects/SCHOLAR_SCOPE/scholarscope_scrapers
# #         print("🔥 DEBUG: STARTING NEW CODE WITH PLAYWRIGHT SETTINGS 🔥")
# #         current_dir = os.path.dirname(os.path.abspath(__file__)) # .../scholarships
# #         django_root = os.path.dirname(current_dir)               # .../scholar_scope
# #         project_root = os.path.dirname(django_root)              # .../SCHOLAR_SCOPE
        
# #         if project_root not in sys.path:
# #             sys.path.append(project_root)

# #         # 2. Dynamic Import (This avoids the ImportError you saw)
# #         # Note: Adjust the import path below to match your actual folder name structure
# #         # If your folder is 'scholarscope_scrapers' and inside is another 'scholarscope_scrapers' folder:
# #         spider_module = importlib.import_module(
# #             'scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider'
# #         )
# #         ScholarshipBatchSpider = getattr(spider_module, 'ScholarshipBatchSpider')

# #         # 3. Configure Scrapy
#         # settings = {
#         #     "ITEM_PIPELINES": {
#         #         "scholarscope.scholarships.pipelines.ScholarshipPipeline": 300,
#         #     },
#         #     "DOWNLOAD_HANDLERS": {
#         #         "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
#         #         "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
#         #     },
#         #     "PLAYWRIGHT_BROWSER_TYPE": "chromium",
#         #     "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
#         #     "LOG_LEVEL": "DEBUG",
#         #     "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
#         #     # 2. Ignore robots.txt (Many sites block bots via this file)
#         #     "ROBOTSTXT_OBEY": False,
            
#         #     # 3. Add common browser headers to look legitimate
#         #     "DEFAULT_REQUEST_HEADERS": {
#         #         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
#         #         "Accept-Language": "en-US,en;q=0.9",
            
#         # } }

# #         # 4. Crawl
# #         process = CrawlerProcess(settings=settings)
# #         process.crawl(
# #             ScholarshipBatchSpider, 
# #             site_config_id=site_config_id, 
# #             scrape_event_id=scrape_event_id
# #         )
# #         process.start()
        
# #     except Exception as e:
# #         print(f"Spider Process Failed: {e}")
# #         # We can't easily log to Django DB from here, so we print to Celery logs
# #         raise e
    
# # @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# # def scrape_site(self, site_config_id, scrape_event_id=None):
# #     try:
# #         site = SiteConfig.objects.get(id=site_config_id)
        
# #         p = multiprocessing.Process(
# #             target=_run_spider_process, 
# #             args=(site_config_id, scrape_event_id)
# #         )
# #         p.start()
# #         p.join() 

# #         # Update Site Config
# #         site.last_scraped = timezone.now()
# #         site.save(update_fields=["last_scraped"])

# #     except Exception as exc:
# #         raise self.retry(exc=exc)

# import django

# def _run_spider_process(site_config_id, scrape_event_id):
#     """Runs in a fresh process with Django properly setup"""
#     try:
#         # 1. Setup Django FIRST
#         os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarscope.settings')
#         django.setup()
        
#         # 2. Now import Django models
#         from scholarships.models import SiteConfig, ScholarshipScrapeEvent
        
#         # 3. Import Scrapy spider
#         import sys
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         project_root = os.path.dirname(os.path.dirname(current_dir))
#         sys.path.insert(0, project_root)
        
#         from scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider import ScholarshipBatchSpider
        
#         # 4. Configure and run
#         from scrapy.crawler import CrawlerProcess
#         # settings = {
#         #     "ITEM_PIPELINES": {
#         #         "scholarscope.scholarships.pipelines.ScholarshipPipeline": 300,
#         #     },
#         #     # ... rest of settings
#         # }
#         settings = {
#             "ITEM_PIPELINES": {
#                 "scholarscope.scholarships.pipelines.ScholarshipPipeline": 300,
#             },
#             "DOWNLOAD_HANDLERS": {
#                 "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
#                 "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
#             },
#             "PLAYWRIGHT_BROWSER_TYPE": "chromium",
#             "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
#             "LOG_LEVEL": "DEBUG",
#             "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
#             # 2. Ignore robots.txt (Many sites block bots via this file)
#             "ROBOTSTXT_OBEY": False,
            
#             # 3. Add common browser headers to look legitimate
#             "DEFAULT_REQUEST_HEADERS": {
#                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
#                 "Accept-Language": "en-US,en;q=0.9",
            
#         } }

        
#         process = CrawlerProcess(settings=settings)
#         process.crawl(
#             ScholarshipBatchSpider,
#             site_config_id=site_config_id,
#             scrape_event_id=scrape_event_id
#         )
#         process.start()
        
#     except Exception as e:
#         print(f"Spider failed: {e}")
#         raise

# @shared_task(bind=True)
# def scrape_site(self, site_config_id, scrape_event_id=None):

#     import multiprocessing
#     p = multiprocessing.Process(
#         target=_run_spider_process,
#         args=(site_config_id, scrape_event_id)
#     )
#     p.start()
#     p.join()
    
#     if p.exitcode != 0:
#         raise Exception(f"Spider process failed with code {p.exitcode}")
    
# @shared_task
# def scrape_all_sources():
#     sources = SiteConfig.objects.filter(active=True)
#     for site in sources:
#         scrape_site.delay(site_config_id=site.id)


# logger = logging.getLogger(__name__)
# def generate_slug(title):
#     return slugify(title)

# def bulk_create(scraped_scholarships, source_name, source_url=None, scrape_event=None):
#     # Create scrape event
#     if not scrape_event:
#         scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
#             source_name=source_name,
#             source_url=source_url
#         )
        
#     try:
#         created_count = 0
#         for scholarship_name, scholarship_entry in scraped_scholarships.items():
#             scholarship_data = scholarship_entry.get('scholarship_data')
            
#             if not scholarship_data:
#                 continue

#             # for field in ["start_date", "end_date"]:
#             #     dt = scholarship_data.get(field)
#             #     if dt and timezone.is_naive(dt):
#             #         scholarship_data[field] = timezone.make_aware(dt)
#             for field in ["start_date", "end_date"]:
#                 dt = scholarship_data.get(field)
#                 if isinstance(dt, datetime) and timezone.is_naive(dt):
#                     scholarship_data[field] = timezone.make_aware(dt)

            

#             link_dict = scholarship_data.get('link')  
#             if isinstance(link_dict, dict):
#                 link = link_dict.get('url', '')
#             else:
#                 link = link_dict or ''

#             if not link:
#                 continue
#             levels = scholarship_data['level']
#             tags = scholarship_data['tags']
#             fingerprint = scholarship_data.get('fingerprint')
#             scholarship = Scholarship(
#                 title=scholarship_data.get('title', scholarship_name),
#                 start_date=scholarship_data.get('start_date'),
#                 end_date=scholarship_data.get('end_date'),
#                 description=scholarship_data.get('description', ''),
#                 reward=scholarship_data.get('reward', ''),
#                 link=link,
#                 requirements=scholarship_data.get('requirements', ''),
#                 eligibility=scholarship_data.get('eligibility', ''),
#                 source=source_name,
#                 scrape_event=scrape_event 
#             )
#             scholarship.fingerprint = fingerprint
            
#             for field in ["title", "reward", "source", "fingerprint", "link"]:
#                 val = getattr(scholarship, field, None)
#                 if isinstance(val, str) and len(val) > 500:
#                     logger.warning("%s length=%s value=%s...", field, len(val), val[:120])
#             logger.debug("About to save scholarship with title=%s", scholarship.title)
#             try:
#                 with transaction.atomic():
#                     scholarship.save()
#             except Exception as e:
#                 logger.warning(f"Skipped scholarship {scholarship_data.get('title')}: {e}")
#             for level in levels:
#                 level, _ = Level.objects.get_or_create(level=level)
#                 scholarship.level.add(level)
#             for tag in tags:
#                 tag, _ = Tag.objects.get_or_create(name=tag)
#                 scholarship.tags.add(tag)
#             created_count += 1

        
        
#         # Update scrape event
#         scrape_event.scholarships_found = len(scraped_scholarships)
#         scrape_event.scholarships_created = created_count
#         scrape_event.scholarships_skipped = len(scraped_scholarships) - created_count
#         scrape_event.mark_completed()
        
#         return created_count
        
#     except Exception as e:
#         scrape_event.mark_failed(str(e))
#         raise

# # @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# # def scrape_single_url(self, url, event_id=None, max_sch=None):
    
# #     try:
# #         scrape_event = None
# #         if event_id:
# #             scrape_event = ScholarshipScrapeEvent.objects.get(id=event_id)
# #         data = scholarscope_scrapers.main_scholarship_scraper(url, max_scholarships=max_sch)
# #         scholarships = data['scholarships']
# #         bulk_create(scholarships, url, url, scrape_event=scrape_event)
# #     except Exception as exc:
# #         raise self.retry(exc=exc)


# # @shared_task
# # def scrape_scholarship_data(max_sch=None):
# #     list_urls = [
# #         "https://scholarsworld.ng/scholarships/top-scholarships/",
# #         "https://scholarsworld.ng/scholarships/undergraduate-scholarships/",
# #         "https://scholarsworld.ng/scholarships/postgraduate-scholarships/",
# #         "https://www.scholarshipregion.com/category/undergraduate-scholarships/",
# #         "https://www.scholarshipregion.com/category/postgraduate-scholarships/",
# #     ]
# #     for url in list_urls:
# #         scrape_single_url(url, max_sch=max_sch)

# @shared_task(bind=True)
# def send_email_reminder(self):
#     try:
#         return ScholarshipEmailService.send_bulk_reminders()
#     except Exception as e:
#         raise self.retry(exc=e, countdown=300, max_retries=2)
    
# @shared_task(bind=True)
# def send_deadline_reminder(self):
#     try:
#         return ScholarshipEmailService.send_deadline_reminder()
#     except Exception as e:
#         raise self.retry(exc=e, countdown=300, max_retries=2)
    
# @shared_task
# def outdated_scholarships():
#     outdated = Scholarship.objects.filter(end_date__lte= timezone.now() - timedelta(days=30))
#     for sch in outdated:
#         sch.active = False
#         sch.save()

# # scholarscope/tasks.py


# # @shared_task(bind=True)
# # def scrape_site(self, list_url, source_name=None):
# #     process = CrawlerProcess(settings={
# #         "ITEM_PIPELINES": {
# #             "scholarscope.scholarships.pipelines.ScholarshipPipeline": 300,
# #         },
# #         "PLAYWRIGHT_BROWSER_TYPE": "chromium",
# #         "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
# #     })
# #     process.crawl(ScholarshipBatchSpider, list_url=list_url, source_name=source_name)
# #     process.start()



# # @shared_task
# # def scrape_all_sources():
# #     sources = SiteConfig.objects.filter(active=True)

# #     for site in sources:
# #         scrape_site.delay(
# #             site_config_id=site.id,
# #         )

    
# # @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# # def scrape_site(self, site_config_id, scrape_event_id=None):
# #     from scrapy.crawler import CrawlerProcess
# #     try:
# #         site = SiteConfig.objects.get(id=site_config_id)
# #         process = CrawlerProcess(settings={
# #             "ITEM_PIPELINES": {
# #                 "scholarscope.scholarships.pipelines.ScholarshipPipeline": 300,
# #             },
# #             "PLAYWRIGHT_BROWSER_TYPE": "chromium",
# #             "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
# #         })
# #         # process = CrawlerProcess(...)
# #         spider_module = importlib.import_module(
# #             'scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider'
# #         )
# #         ScholarshipBatchSpider = getattr(spider_module, 'ScholarshipBatchSpider')
# #         process.crawl(ScholarshipBatchSpider,
# #                      site_config_id=site_config_id, scrape_event_id=scrape_event_id)

# #         process.start()

# #         site.last_scraped = timezone.now()
# #         site.save(update_fields=["last_scraped"])

# #     except Exception as exc:
# #         raise self.retry(exc=exc)
    
# @shared_task
# def generate_scholarship_embedding(scholarship_id):
#     s = Scholarship.objects.get(id=scholarship_id)
#     text = f"{s.title}. {s.description}. {s.eligibility or ''}. {s.requirements or ''}"
#     s.embedding = get_text_embedding(text)
#     s.save(update_fields=["embedding", "updated_at"])

# @shared_task
# def generate_profile_embedding(profile_id):
#     profile = Profile.objects.get(id=profile_id)
#     text = f"{profile.field_of_study}. {profile.bio}. {profile.preferred_scholarship_types}. {profile.preferred_countries}"
#     profile.embedding = get_text_embedding(text)
#     profile.save(update_fields=["embedding", "updated_at"])
#     cache.delete(f"user_recommendations_{profile.user.id}")

# @shared_task
# def batch_invalidate_user_recommendations(user_ids):
#     for uid in user_ids:
#         cache.delete(_rec_cache_key(uid))



# # import subprocess
# # import sys
# # from celery import shared_task
# # from django.utils import timezone
# # from scholarships.models import SiteConfig


# # @shared_task
# # def scrape_all_sources():
# #     for site in SiteConfig.objects.filter(active=True):
# #         scrape_site.delay(site.id)


# # @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# # def scrape_site(self, site_config_id, scrape_event_id=None):
# #     try:
# #         cmd = [
# #             sys.executable,  # the same Python environment Celery uses
# #             "-m",
# #             "scrapy",
# #             "crawl",
# #             "scholarship_batch",
# #             "-a",
# #             f"site_config_id={site_config_id}",
# #         ]

# #         if scrape_event_id:
# #             cmd.append(f"-a scrape_event_id={scrape_event_id}")

# #         # Run the spider in a *separate process*
# #         subprocess.check_call(cmd)

# #         site = SiteConfig.objects.get(id=site_config_id)
# #         site.last_scraped = timezone.now()
# #         site.save(update_fields=["last_scraped"])

# #     except Exception as exc:
# #         raise self.retry(exc=exc)

# # scholarships/tasks.py
# # import subprocess
# # import shlex
# # from celery import shared_task
# # from django.utils import timezone
# # from scholarships.models import SiteConfig


# # @shared_task(bind=True, max_retries=5, default_retry_delay=120)
# # def scrape_site(self, site_config_id, scrape_event_id=None):
# #     try:
# #         site = SiteConfig.objects.get(id=site_config_id)
        
# #         # Build the exact same command you'd run in terminal
# #         cmd = [
# #             "scrapy", "crawl", "scholarship_batch",
# #             "-a", f"site_config_id={site_config_id}",
# #             "-a", f"max_items=100"
# #         ]
        
# #         if scrape_event_id:
# #             cmd += ["-a", f"scrape_event_id={scrape_event_id}"]

# #         # Run as subprocess — completely isolated
# #         result = subprocess.run(
# #             cmd,
# #             cwd="scholarscope_scrapers",  # important: run from scrapy project root
# #             capture_output=True,
# #             text=True,
# #             timeout=600  # 10 minutes max
# #         )

# #         if result.returncode != 0:
# #             raise Exception(f"Scrapy failed: {result.stderr}")

# #         # Success!
# #         site.last_scraped = timezone.now()
# #         site.save(update_fields=["last_scraped"])

# #     except subprocess.TimeoutExpired:
# #         raise self.retry(countdown=300, exc=Exception("Scrapy timeout"))
# #     except Exception as exc:
# #         raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

# # Render Free Tier:
# #     - Django
# #     - Celery (only for email & cleanup)
# #     - API

# # External Worker (GitHub Actions / local machine / VPS):
# #     - Scrapy Playwright spider
# #     - Chromium

# # from celery import shared_task, chord
# # from django.utils import timezone
# # from .models import SiteConfig, Scholarship, ScholarshipScrapeEvent
# # from scholarscope_scrapers.scraping3 import ScholarshipListScraper, ScholarshipScraper
# # @shared_task
# # def scrape_all_sources():
# #     """Schedule scraping for all active sources."""
# #     sources = SiteConfig.objects.filter(active=True)
# #     for site in sources:
# #         scrape_site.delay(site_config_id=site.id)

# # def save_scholarship_detail(data, source_name, source_url, scrape_event):
# #     """
# #     Save ONE scholarship cleanly.
# #     Called by: scrape_scholarship_detail Celery task.
# #     """

# #     if not data:
# #         return None

# #     # --- Extract core fields ---
# #     title = data.get("title") or "Untitled Scholarship"
# #     link = data.get("link", "")
# #     if isinstance(link, dict):
# #         link = link.get("url", "")

# #     if not link:
# #         # invalid entry
# #         return None

# #     # Fix dates
# #     for f in ("start_date", "end_date"):
# #         dt = data.get(f)
# #         if isinstance(dt, timezone.datetime) and timezone.is_naive(dt):
# #             data[f] = timezone.make_aware(dt)

# #     levels = data.get("level", [])
# #     tags = data.get("tags", [])
# #     fingerprint = data.get("fingerprint")

# #     # --- Save or update ---
# #     with transaction.atomic():
# #         scholarship, created = Scholarship.objects.update_or_create(
# #             fingerprint=fingerprint,
# #             defaults={
# #                 "title": title,
# #                 "start_date": data.get("start_date"),
# #                 "end_date": data.get("end_date"),
# #                 "description": data.get("description", ""),
# #                 "reward": data.get("reward", ""),
# #                 "link": link,
# #                 "requirements": data.get("requirements", ""),
# #                 "eligibility": data.get("eligibility", ""),
# #                 "source": source_name,
# #                 "scrape_event": scrape_event,
# #             },
# #         )

# #         # --- Update M2M ---
# #         scholarship.level.clear()
# #         scholarship.tags.clear()

# #         for lvl in levels:
# #             lvl_obj, _ = Level.objects.get_or_create(level=lvl)
# #             scholarship.level.add(lvl_obj)

# #         for t in tags:
# #             tag_obj, _ = Tag.objects.get_or_create(name=t)
# #             scholarship.tags.add(tag_obj)

# #     return scholarship

# # @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# # def scrape_scholarship_detail(self, url, site_id, scrape_event_id):
# #     try:
# #         site = SiteConfig.objects.get(id=site_id)
# #         scrape_event = ScholarshipScrapeEvent.objects.get(id=scrape_event_id)

# #         scraper = ScholarshipScraper(site_config=site)  # whatever scraper returns
# #         data = scraper.scrape(url)
# #         save_scholarship_detail(
# #             data=data,
# #             source_name=site.name,
# #             source_url=site.list_url,
# #             scrape_event=scrape_event
# #         )

# #     except Exception as e:
# #         if self.request.retries < self.max_retries:
# #             raise self.retry(exc=e)    
# #         FailedScholarship.objects.create(
# #             scrape_event_id=scrape_event_id,
# #             url=url,
# #             reason=str(e)
# #         )
# #         raise



# # @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# # def scrape_site(self, site_config_id, scrape_event_id=None, max_items=50, delay_between_scrapes=2):
# #     try:
# #         site = SiteConfig.objects.get(id=site_config_id)

# #         # 1. Start scrape event
# #         if not scrape_event_id:
# #             scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
# #                 source_name=site.name,
# #                 source_url=site.list_url
# #             )
# #         else:
# #             scrape_event = ScholarshipScrapeEvent.objects.get(id=scrape_event_id)

# #         # 2. Scrape list page for scholarships
# #         list_scraper = ScholarshipListScraper(site_config=site, max_items=max_items, delay=delay_between_scrapes)
# #         scraped_list = list_scraper.scrape_list()

# #         if not scraped_list:
# #             scrape_event.mark_failed("No scholarships found on list page")
# #             return

# #         # 3. Schedule individual detail scrapes as Celery tasks
# #         detail_tasks = []
# #         for item in scraped_list:
# #             detail_tasks.append(scrape_scholarship_detail.s(item['url'], site.id, scrape_event.id))

# #         # Run all detail tasks as a group
# #         chord(detail_tasks)(finalize_scrape_event.s(scrape_event.id))
# #         # for item in scraped_list:
# #         #     scrape_scholarship_detail(url=item['url'], site_id=site.id, scrape_event_id=scrape_event.id)


# #         # 4. Update site last_scraped timestamp
# #         site.last_scraped = timezone.now()
# #         site.save(update_fields=["last_scraped"])

# #         return f"Scheduled {len(scraped_list)} scholarships for detail scraping"

# #     except Exception as exc:
# #         raise self.retry(exc=exc)



# @shared_task
# def finalize_scrape_event(results, scrape_event_id):
#     event = ScholarshipScrapeEvent.objects.get(id=scrape_event_id)

#     failed = FailedScholarship.objects.filter(scrape_event=event).exists()

#     if failed:
#         event.mark_partial("Some scholarships failed — see FailedScholarship table")
#     else:
#         event.mark_success()

#     return "Scrape event completed"

import sys
import os
import django
import logging
import multiprocessing 
from celery import shared_task
from scrapy.crawler import CrawlerProcess
import numpy as np
from django.utils import timezone
from sklearn.metrics.pairwise import cosine_similarity
from datetime import timedelta
from django.core.mail import send_mail
logger = logging.getLogger(__name__)


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

def _run_spider_process(site_config_id, scrape_event_id):
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarscope.settings')
        django.setup()

        from scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider import ScholarshipBatchSpider
        settings = {
            # Pipeline Path
            "ITEM_PIPELINES": {
                'scholarscope_scrapers.scholarscope_scrapers.pipelines.RenewalAndDuplicatePipeline': 200,
                'scholarscope_scrapers.scholarscope_scrapers.pipelines.ScholarshipPipeline': 300,
            },
            "PLAYWRIGHT_ABORT_REQUEST": should_abort_request,
            # Playwright Handlers
            "DOWNLOAD_HANDLERS": {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            
            "PLAYWRIGHT_BROWSER_TYPE": "firefox",
            
            "PLAYWRIGHT_LAUNCH_OPTIONS": {
                "headless": True,
                "timeout": 60000, # 60s timeout
            },
            
            "PLAYWRIGHT_CONTEXT_ARGS": {
                "ignore_https_errors": True, # Ignore SSL/TLS certificate errors
                "java_script_enabled": True,
                "bypass_csp": True,
                
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
                
                "viewport": {"width": 1280, "height": 720},
                "service_workers": "block",
            },

            # ✅ Scrapy Config
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            "LOG_LEVEL": "DEBUG",
            "ROBOTSTXT_OBEY": False,
            "COOKIES_ENABLED": True,
            "HTTPERROR_ALLOWED_CODES": [403, 404, 500],
            
            "USER_AGENT": None, 
        }

        # 5. RUN CRAWLER
        process = CrawlerProcess(settings=settings)
        process.crawl(
            ScholarshipBatchSpider, 
            site_config_id=site_config_id, 
            scrape_event_id=scrape_event_id
        )
        process.start()

    except Exception as e:
        print(f"Spider Process Failed: {e}")
        sys.exit(1) # Exit with error code so Celery knows it failed


@shared_task(bind=True)
def scrape_site(self, site_config_id, scrape_event_id=None):
    from scholarships.models import SiteConfig 
    from django.utils import timezone

    p = multiprocessing.Process(
        target=_run_spider_process, 
        args=(site_config_id, scrape_event_id)
    )
    p.start()
    p.join() 
    
    # Check if it crashed
    if p.exitcode != 0:
        raise Exception(f"Spider process failed with code {p.exitcode}")

    # Success: Update Timestamp
    try:
        site = SiteConfig.objects.get(id=site_config_id)
        site.last_scraped = timezone.now()
        site.save(update_fields=["last_scraped"])
    except SiteConfig.DoesNotExist:
        pass

@shared_task
def scrape_all_sources():
    # 👇 Local import
    from scholarships.models import SiteConfig
    sources = SiteConfig.objects.filter(active=True)
    for site in sources:
        scrape_site.delay(site_config_id=site.id)


@shared_task(bind=True)
def send_email_reminder(self):
    from scholarships.services import ScholarshipEmailService
    try:
        return ScholarshipEmailService.send_bulk_reminders()
    except Exception as e:
        raise self.retry(exc=e, countdown=300, max_retries=2)
    
@shared_task(bind=True)
def send_deadline_reminder(self):
    from scholarships.services import ScholarshipEmailService
    try:
        return ScholarshipEmailService.send_deadline_reminder()
    except Exception as e:
        raise self.retry(exc=e, countdown=300, max_retries=2)
    
@shared_task
def outdated_scholarships():
    from scholarships.models import Scholarship
    from django.utils import timezone
    from datetime import timedelta
    
    outdated = Scholarship.objects.filter(end_date__lte= timezone.now() - timedelta(days=30))
    for sch in outdated:
        sch.active = False
        sch.save()

@shared_task
def generate_scholarship_embedding(scholarship_id):
    from scholarships.models import Scholarship
    from scholarships.utils import get_text_embedding
    
    s = Scholarship.objects.get(id=scholarship_id)
    text = f"{s.title}. {s.description}. {s.eligibility or ''}. {s.requirements or ''}"
    s.embedding = get_text_embedding(text)
    s.save(update_fields=["embedding"])

@shared_task
def generate_profile_embedding(profile_id):
    from scholarships.models import Profile
    from scholarships.utils import get_text_embedding
    from django.core.cache import cache
    
    profile = Profile.objects.get(id=profile_id)
    text = f"{profile.field_of_study}. {profile.bio}. {profile.preferred_scholarship_types}. {profile.preferred_countries}"
    profile.embedding = get_text_embedding(text)
    profile.save(update_fields=["embedding", "updated_at"])
    # Note: Ensure _rec_cache_key logic is consistent or imported locally
    cache.delete(f"user_recommendations_{profile.user.id}")

@shared_task
def batch_invalidate_user_recommendations(user_ids):
    from django.core.cache import cache
    from scholarships.utils import _rec_cache_key
    for uid in user_ids:
        cache.delete(_rec_cache_key(uid))

@shared_task
def finalize_scrape_event(results, scrape_event_id):
    from scholarships.models import ScholarshipScrapeEvent, FailedScholarship
    event = ScholarshipScrapeEvent.objects.get(id=scrape_event_id)
    failed = FailedScholarship.objects.filter(scrape_event=event).exists()
    if failed:
        event.mark_partial("Some scholarships failed — see FailedScholarship table")
    else:
        event.mark_success()
    return "Scrape event completed"

@shared_task
def remove_semantic_duplicates(threshold=0.95):
    from scholarships.models import Scholarship
    print("Starting Semantic Deduplication...")
    scholarships = list(Scholarship.objects.filter(
        active=True, 
        embedding__isnull=False
    ).values('id', 'title', 'embedding', 'description'))
    
    if len(scholarships) < 2:
        return "Not enough items to check."


    embeddings = np.array([s['embedding'] for s in scholarships])
    ids = [s['id'] for s in scholarships]
    
    similarity_matrix = cosine_similarity(embeddings)
    
    upper_triangle = np.triu(similarity_matrix, k=1)
    
    duplicate_indices = np.where(upper_triangle > threshold)
    
    deleted_count = 0
    deleted_ids = set()

    # Zip turns the two arrays into pairs of (i, j)
    for i, j in zip(*duplicate_indices):
        id_a = ids[i]
        id_b = ids[j]
        
        # Skip if we already deleted one of them
        if id_a in deleted_ids or id_b in deleted_ids:
            continue
            
        item_a = scholarships[i]
        item_b = scholarships[j]
        
        print(f"MATCH FOUND ({upper_triangle[i][j]:.3f}):")
        print(f"   A: {item_a['title']}")
        print(f"   B: {item_b['title']}")
        
        
        len_a = len(item_a['description'] or "")
        len_b = len(item_b['description'] or "")
        
        id_to_delete = id_b if len_a >= len_b else id_a
        
        Scholarship.objects.filter(id=id_to_delete).delete()
        deleted_ids.add(id_to_delete)
        deleted_count += 1
    return f"Cleanup Complete. Removed {deleted_count} semantic duplicates."

@shared_task
def send_weekly_renewal_notifications():
    from scholarships.models import WatchedScholarship, Scholarship
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    renewed_scholarships = Scholarship.objects.filter(
        status='active',
        last_renewed_at__gte=seven_days_ago
    )
    
    if not renewed_scholarships.exists():
        return "No renewals this week."

    print(f"Processing notifications for {renewed_scholarships.count()} renewed scholarships...")

    emails_sent = 0
    
    for scholarship in renewed_scholarships:
        current_year = timezone.now().year
        watchers = WatchedScholarship.objects.filter(
            scholarship=scholarship
        ).exclude(notified_for_year=current_year).select_related('user')
        
        for watch in watchers:
            user = watch.user
            if not user.email: continue
            
            subject = f"Action Required: {scholarship.title} is Open!"
            message = (
                f"Hello {user.first_name},\n\n"
                f"The scholarship you are tracking, '{scholarship.title}', "
                f"has reopened for the new cycle.\n\n"
                f"📅 Deadline: {scholarship.latest_deadline}\n"
                f"🔗 Apply: {scholarship.link}\n\n"
                f"Good luck!"
            )
            
            try:
                send_mail(subject, message, 'noreply@scholarscope.com', [user.email])
                
                watch.notified_for_year = current_year
                watch.save()
                emails_sent += 1
            except Exception as e:
                print(f"Error emailing user {user.id}: {e}")

    return f"Sent {emails_sent} renewal notifications."