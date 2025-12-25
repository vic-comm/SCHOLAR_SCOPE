from celery import shared_task
from .models import Scholarship, ScholarshipScrapeEvent, Level, Tag, SiteConfig, Profile, FailedScholarship
from django.utils import timezone
from django.utils.text import slugify
from scholarships.services import ScholarshipEmailService
from scholarships.utils import random_string_generator
from django.core.cache import cache
from datetime import datetime, timedelta
from django.db import transaction
from scholarships.utils import generate_fingerprint, get_text_embedding, _rec_cache_key
import os
os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'scholarscope_scrapers.settings')
import importlib
# from scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider import ScholarshipBatchSpider
# from ..scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider import ScholarshipBatchSpider
# from scholarscope_scrapers.spiders.scholarships_spider import ScholarshipBatchSpider
import logging



logger = logging.getLogger(__name__)
def generate_slug(title):
    return slugify(title)

def bulk_create(scraped_scholarships, source_name, source_url=None, scrape_event=None):
    # Create scrape event
    if not scrape_event:
        scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
            source_name=source_name,
            source_url=source_url
        )
        
    try:
        created_count = 0
        for scholarship_name, scholarship_entry in scraped_scholarships.items():
            scholarship_data = scholarship_entry.get('scholarship_data')
            
            if not scholarship_data:
                continue

            # for field in ["start_date", "end_date"]:
            #     dt = scholarship_data.get(field)
            #     if dt and timezone.is_naive(dt):
            #         scholarship_data[field] = timezone.make_aware(dt)
            for field in ["start_date", "end_date"]:
                dt = scholarship_data.get(field)
                if isinstance(dt, datetime) and timezone.is_naive(dt):
                    scholarship_data[field] = timezone.make_aware(dt)

            

            link_dict = scholarship_data.get('link')  
            if isinstance(link_dict, dict):
                link = link_dict.get('url', '')
            else:
                link = link_dict or ''

            if not link:
                continue
            levels = scholarship_data['level']
            tags = scholarship_data['tags']
            fingerprint = scholarship_data.get('fingerprint')
            scholarship = Scholarship(
                title=scholarship_data.get('title', scholarship_name),
                start_date=scholarship_data.get('start_date'),
                end_date=scholarship_data.get('end_date'),
                description=scholarship_data.get('description', ''),
                reward=scholarship_data.get('reward', ''),
                link=link,
                requirements=scholarship_data.get('requirements', ''),
                eligibility=scholarship_data.get('eligibility', ''),
                source=source_name,
                scrape_event=scrape_event 
            )
            scholarship.fingerprint = fingerprint
            
            for field in ["title", "reward", "source", "fingerprint", "link"]:
                val = getattr(scholarship, field, None)
                if isinstance(val, str) and len(val) > 500:
                    logger.warning("%s length=%s value=%s...", field, len(val), val[:120])
            logger.debug("About to save scholarship with title=%s", scholarship.title)
            try:
                with transaction.atomic():
                    scholarship.save()
            except Exception as e:
                logger.warning(f"Skipped scholarship {scholarship_data.get('title')}: {e}")
            for level in levels:
                level, _ = Level.objects.get_or_create(level=level)
                scholarship.level.add(level)
            for tag in tags:
                tag, _ = Tag.objects.get_or_create(name=tag)
                scholarship.tags.add(tag)
            created_count += 1

        
        
        # Update scrape event
        scrape_event.scholarships_found = len(scraped_scholarships)
        scrape_event.scholarships_created = created_count
        scrape_event.scholarships_skipped = len(scraped_scholarships) - created_count
        scrape_event.mark_completed()
        
        return created_count
        
    except Exception as e:
        scrape_event.mark_failed(str(e))
        raise

# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def scrape_single_url(self, url, event_id=None, max_sch=None):
    
#     try:
#         scrape_event = None
#         if event_id:
#             scrape_event = ScholarshipScrapeEvent.objects.get(id=event_id)
#         data = scholarscope_scrapers.main_scholarship_scraper(url, max_scholarships=max_sch)
#         scholarships = data['scholarships']
#         bulk_create(scholarships, url, url, scrape_event=scrape_event)
#     except Exception as exc:
#         raise self.retry(exc=exc)


# @shared_task
# def scrape_scholarship_data(max_sch=None):
#     list_urls = [
#         "https://scholarsworld.ng/scholarships/top-scholarships/",
#         "https://scholarsworld.ng/scholarships/undergraduate-scholarships/",
#         "https://scholarsworld.ng/scholarships/postgraduate-scholarships/",
#         "https://www.scholarshipregion.com/category/undergraduate-scholarships/",
#         "https://www.scholarshipregion.com/category/postgraduate-scholarships/",
#     ]
#     for url in list_urls:
#         scrape_single_url(url, max_sch=max_sch)

@shared_task(bind=True)
def send_email_reminder(self):
    try:
        return ScholarshipEmailService.send_bulk_reminders()
    except Exception as e:
        raise self.retry(exc=e, countdown=300, max_retries=2)
    
@shared_task(bind=True)
def send_deadline_reminder(self):
    try:
        return ScholarshipEmailService.send_deadline_reminder()
    except Exception as e:
        raise self.retry(exc=e, countdown=300, max_retries=2)
    
@shared_task
def outdated_scholarships():
    outdated = Scholarship.objects.filter(end_date__lte= timezone.now() - timedelta(days=30))
    for sch in outdated:
        sch.active = False
        sch.save()

# scholarscope/tasks.py


# @shared_task(bind=True)
# def scrape_site(self, list_url, source_name=None):
#     process = CrawlerProcess(settings={
#         "ITEM_PIPELINES": {
#             "scholarscope.scholarships.pipelines.ScholarshipPipeline": 300,
#         },
#         "PLAYWRIGHT_BROWSER_TYPE": "chromium",
#         "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
#     })
#     process.crawl(ScholarshipBatchSpider, list_url=list_url, source_name=source_name)
#     process.start()



# @shared_task
# def scrape_all_sources():
#     sources = SiteConfig.objects.filter(active=True)

#     for site in sources:
#         scrape_site.delay(
#             site_config_id=site.id,
#         )

    
# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def scrape_site(self, site_config_id, scrape_event_id=None):
#     from scrapy.crawler import CrawlerProcess
#     try:
#         site = SiteConfig.objects.get(id=site_config_id)
#         process = CrawlerProcess(settings={
#             "ITEM_PIPELINES": {
#                 "scholarscope.scholarships.pipelines.ScholarshipPipeline": 300,
#             },
#             "PLAYWRIGHT_BROWSER_TYPE": "chromium",
#             "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
#         })
#         # process = CrawlerProcess(...)
#         spider_module = importlib.import_module(
#             'scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider'
#         )
#         ScholarshipBatchSpider = getattr(spider_module, 'ScholarshipBatchSpider')
#         process.crawl(ScholarshipBatchSpider,
#                      site_config_id=site_config_id, scrape_event_id=scrape_event_id)

#         process.start()

#         site.last_scraped = timezone.now()
#         site.save(update_fields=["last_scraped"])

#     except Exception as exc:
#         raise self.retry(exc=exc)
    
@shared_task
def generate_scholarship_embedding(scholarship_id):
    s = Scholarship.objects.get(id=scholarship_id)
    text = f"{s.title}. {s.description}. {s.eligibility or ''}. {s.requirements or ''}"
    s.embedding = get_text_embedding(text)
    s.save(update_fields=["embedding", "updated_at"])

@shared_task
def generate_profile_embedding(profile_id):
    profile = Profile.objects.get(id=profile_id)
    text = f"{profile.field_of_study}. {profile.bio}. {profile.preferred_scholarship_types}. {profile.preferred_countries}"
    profile.embedding = get_text_embedding(text)
    profile.save(update_fields=["embedding", "updated_at"])
    cache.delete(f"user_recommendations_{profile.user.id}")

@shared_task
def batch_invalidate_user_recommendations(user_ids):
    for uid in user_ids:
        cache.delete(_rec_cache_key(uid))



# import subprocess
# import sys
# from celery import shared_task
# from django.utils import timezone
# from scholarships.models import SiteConfig


# @shared_task
# def scrape_all_sources():
#     for site in SiteConfig.objects.filter(active=True):
#         scrape_site.delay(site.id)


# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def scrape_site(self, site_config_id, scrape_event_id=None):
#     try:
#         cmd = [
#             sys.executable,  # the same Python environment Celery uses
#             "-m",
#             "scrapy",
#             "crawl",
#             "scholarship_batch",
#             "-a",
#             f"site_config_id={site_config_id}",
#         ]

#         if scrape_event_id:
#             cmd.append(f"-a scrape_event_id={scrape_event_id}")

#         # Run the spider in a *separate process*
#         subprocess.check_call(cmd)

#         site = SiteConfig.objects.get(id=site_config_id)
#         site.last_scraped = timezone.now()
#         site.save(update_fields=["last_scraped"])

#     except Exception as exc:
#         raise self.retry(exc=exc)

# scholarships/tasks.py
# import subprocess
# import shlex
# from celery import shared_task
# from django.utils import timezone
# from scholarships.models import SiteConfig


# @shared_task(bind=True, max_retries=5, default_retry_delay=120)
# def scrape_site(self, site_config_id, scrape_event_id=None):
#     try:
#         site = SiteConfig.objects.get(id=site_config_id)
        
#         # Build the exact same command you'd run in terminal
#         cmd = [
#             "scrapy", "crawl", "scholarship_batch",
#             "-a", f"site_config_id={site_config_id}",
#             "-a", f"max_items=100"
#         ]
        
#         if scrape_event_id:
#             cmd += ["-a", f"scrape_event_id={scrape_event_id}"]

#         # Run as subprocess — completely isolated
#         result = subprocess.run(
#             cmd,
#             cwd="scholarscope_scrapers",  # important: run from scrapy project root
#             capture_output=True,
#             text=True,
#             timeout=600  # 10 minutes max
#         )

#         if result.returncode != 0:
#             raise Exception(f"Scrapy failed: {result.stderr}")

#         # Success!
#         site.last_scraped = timezone.now()
#         site.save(update_fields=["last_scraped"])

#     except subprocess.TimeoutExpired:
#         raise self.retry(countdown=300, exc=Exception("Scrapy timeout"))
#     except Exception as exc:
#         raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

# Render Free Tier:
#     - Django
#     - Celery (only for email & cleanup)
#     - API

# External Worker (GitHub Actions / local machine / VPS):
#     - Scrapy Playwright spider
#     - Chromium

from celery import shared_task, chord
from django.utils import timezone
from .models import SiteConfig, Scholarship, ScholarshipScrapeEvent
from scholarscope_scrapers.scraping3 import ScholarshipListScraper, ScholarshipScraper
@shared_task
def scrape_all_sources():
    """Schedule scraping for all active sources."""
    sources = SiteConfig.objects.filter(active=True)
    for site in sources:
        scrape_site.delay(site_config_id=site.id)

def save_scholarship_detail(data, source_name, source_url, scrape_event):
    """
    Save ONE scholarship cleanly.
    Called by: scrape_scholarship_detail Celery task.
    """

    if not data:
        return None

    # --- Extract core fields ---
    title = data.get("title") or "Untitled Scholarship"
    link = data.get("link", "")
    if isinstance(link, dict):
        link = link.get("url", "")

    if not link:
        # invalid entry
        return None

    # Fix dates
    for f in ("start_date", "end_date"):
        dt = data.get(f)
        if isinstance(dt, timezone.datetime) and timezone.is_naive(dt):
            data[f] = timezone.make_aware(dt)

    levels = data.get("level", [])
    tags = data.get("tags", [])
    fingerprint = data.get("fingerprint")

    # --- Save or update ---
    with transaction.atomic():
        scholarship, created = Scholarship.objects.update_or_create(
            fingerprint=fingerprint,
            defaults={
                "title": title,
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "description": data.get("description", ""),
                "reward": data.get("reward", ""),
                "link": link,
                "requirements": data.get("requirements", ""),
                "eligibility": data.get("eligibility", ""),
                "source": source_name,
                "scrape_event": scrape_event,
            },
        )

        # --- Update M2M ---
        scholarship.level.clear()
        scholarship.tags.clear()

        for lvl in levels:
            lvl_obj, _ = Level.objects.get_or_create(level=lvl)
            scholarship.level.add(lvl_obj)

        for t in tags:
            tag_obj, _ = Tag.objects.get_or_create(name=t)
            scholarship.tags.add(tag_obj)

    return scholarship

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_scholarship_detail(self, url, site_id, scrape_event_id):
    try:
        site = SiteConfig.objects.get(id=site_id)
        scrape_event = ScholarshipScrapeEvent.objects.get(id=scrape_event_id)

        scraper = ScholarshipScraper(site_config=site)  # whatever scraper returns
        data = scraper.scrape(url)
        save_scholarship_detail(
            data=data,
            source_name=site.name,
            source_url=site.list_url,
            scrape_event=scrape_event
        )

    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)    
        FailedScholarship.objects.create(
            scrape_event_id=scrape_event_id,
            url=url,
            reason=str(e)
        )
        raise



@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_site(self, site_config_id, scrape_event_id=None, max_items=50, delay_between_scrapes=2):
    try:
        site = SiteConfig.objects.get(id=site_config_id)

        # 1. Start scrape event
        if not scrape_event_id:
            scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
                source_name=site.name,
                source_url=site.list_url
            )
        else:
            scrape_event = ScholarshipScrapeEvent.objects.get(id=scrape_event_id)

        # 2. Scrape list page for scholarships
        list_scraper = ScholarshipListScraper(site_config=site, max_items=max_items, delay=delay_between_scrapes)
        scraped_list = list_scraper.scrape_list()

        if not scraped_list:
            scrape_event.mark_failed("No scholarships found on list page")
            return

        # 3. Schedule individual detail scrapes as Celery tasks
        detail_tasks = []
        for item in scraped_list:
            detail_tasks.append(scrape_scholarship_detail.s(item['url'], site.id, scrape_event.id))

        # Run all detail tasks as a group
        chord(detail_tasks)(finalize_scrape_event.s(scrape_event.id))
        # for item in scraped_list:
        #     scrape_scholarship_detail(url=item['url'], site_id=site.id, scrape_event_id=scrape_event.id)


        # 4. Update site last_scraped timestamp
        site.last_scraped = timezone.now()
        site.save(update_fields=["last_scraped"])

        return f"Scheduled {len(scraped_list)} scholarships for detail scraping"

    except Exception as exc:
        raise self.retry(exc=exc)



@shared_task
def finalize_scrape_event(results, scrape_event_id):
    event = ScholarshipScrapeEvent.objects.get(id=scrape_event_id)

    failed = FailedScholarship.objects.filter(scrape_event=event).exists()

    if failed:
        event.mark_partial("Some scholarships failed — see FailedScholarship table")
    else:
        event.mark_success()

    return "Scrape event completed"
