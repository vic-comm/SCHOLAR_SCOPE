from celery import shared_task
from .models import Scholarship, ScholarshipScrapeEvent, Level, Tag, SiteConfig, Profile
from django.utils import timezone
from django.utils.text import slugify
from scholarships.services import ScholarshipEmailService
from scholarships.utils import random_string_generator
from django.core.cache import cache
from datetime import datetime, timedelta
from django.db import transaction
from scholarships.utils import generate_fingerprint, get_text_embedding, _rec_cache_key
from celery import shared_task
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



@shared_task
def scrape_all_sources():
    sources = SiteConfig.objects.filter(active=True)

    for site in sources:
        scrape_site.delay(
            site_config_id=site.id,
        )

    
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_site(self, site_config_id, scrape_event_id=None):
    from scrapy.crawler import CrawlerProcess
    try:
        site = SiteConfig.objects.get(id=site_config_id)
        process = CrawlerProcess(settings={
            "ITEM_PIPELINES": {
                "scholarscope.scholarships.pipelines.ScholarshipPipeline": 300,
            },
            "PLAYWRIGHT_BROWSER_TYPE": "chromium",
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        })
        # process = CrawlerProcess(...)
        spider_module = importlib.import_module(
            'scholarscope_scrapers.scholarscope_scrapers.spiders.scholarships_spider'
        )
        ScholarshipBatchSpider = getattr(spider_module, 'ScholarshipBatchSpider')
        process.crawl(ScholarshipBatchSpider,
                     site_config_id=site_config_id, scrape_event_id=scrape_event_id)

        process.start()

        site.last_scraped = timezone.now()
        site.save(update_fields=["last_scraped"])

    except Exception as exc:
        raise self.retry(exc=exc)
    
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
