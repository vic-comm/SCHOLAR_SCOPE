from celery import shared_task
import helpers
from .models import Scholarship, ScholarshipScrapeEvent, Level, Tag
from django.utils import timezone
from django.utils.text import slugify
from scholarships.services import ScholarshipEmailService
from scholarships.utils import random_string_generator
import hashlib
# from helpers import llm_extract 
from datetime import timedelta
import platform
import asyncio

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
def generate_slug(title):
    return slugify(title)

def generate_fingerprint(title, link):
        base = f"{title.lower().strip()}-{link}"
        return hashlib.sha256(base.encode()).hexdigest()

def bulk_create(scraped_scholarships, source_name, source_url=None, scrape_event=None):
    # Create scrape event
    if not scrape_event:
        scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
            source_name=source_name,
            source_url=source_url
        )
        
    try:
        existing_fingerprints = set(Scholarship.objects.values_list('fingerprint', flat=True))

        created_count = 0
        for scholarship_name, scholarship_entry in scraped_scholarships.items():
            scholarship_data = scholarship_entry.get('scholarship_data')
            
            if not scholarship_data:
                continue

            link_dict = scholarship_data.get('link')  
            if isinstance(link_dict, dict):
                link = link_dict.get('url', '')
            else:
                link = link_dict or ''

            if not link:
                continue
            levels = scholarship_data['level']
            tags = scholarship_data['tags']
            fingerprint = generate_fingerprint(scholarship_data['title'], scholarship_data['link']) 
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
            scholarship.save()
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

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_single_url(self, url, event_id=None):
    
    try:
        scrape_event = None
        if event_id:
            scrape_event = ScholarshipScrapeEvent.objects.get(id=event_id)
        data = helpers.main_scholarship_scraper(url, 5)
        scholarships = data['scholarships']
        bulk_create(scholarships, url, url, scrape_event=scrape_event)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def scrape_scholarship_data():
    list_urls = [
        "https://www.scholarshipregion.com/category/undergraduate-scholarships/",
        # "https://www.scholarshipregion.com/category/postgraduate-scholarships/",
        
    ]
    for url in list_urls:
        scrape_single_url(url)

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
def delete_outdated_scholarships():
    outdated = Scholarship.objects.filter(end_date__lte= timezone.now() - timedelta(days=30))
    outdated.delete()