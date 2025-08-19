from celery import shared_task
import helpers
from .models import Scholarship, ScholarshipScrapeEvent, Application
from django.utils import timezone
from django.utils.text import slugify
from scholarships.services import ScholarshipEmailService
from scholarships.utils import random_string_generator

def unique_slug_generator(instance, new_slug=None):
    """
    This is for a Django project and it assumes your instance 
    has a model with a slug field and a title character (char) field.
    """
    if new_slug is not None:
        slug = new_slug
    else:
        slug = slugify(instance.title)

    Klass = instance.__class__
    qs_exists = Klass.objects.filter(slug=slug).exists()
    if qs_exists:
        new_slug = "{slug}-{randstr}".format(
                    slug=slug,
                    randstr=random_string_generator(size=4)
                )
        return unique_slug_generator(instance, new_slug=new_slug)
    return slug

def bulk_create(scraped_scholarships, source_name, source_url=None):
    # Create scrape event
    scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
        source_name=source_name,
        source_url=source_url
    )
    
    try:
        # Check for existing scholarships
        existing_links = set(

            Scholarship.objects.values_list('link', flat=True)
        )

        new_scholarships = []
        for scholarship_title, scholarship_data in scraped_scholarships:
            scholarship_data = scholarship_title['scholarship_data']

            if scholarship_data['link'] not in existing_links:
                scholarship = Scholarship(
                    title=scholarship_data['title'],
                    start_date=scholarship_data['start_date'],
                    end_date=scholarship_data['end_date'],
                    tags=scholarship_data['tags'],
                    description=scholarship_data['description'],
                    reward=scholarship_data['reward'],
                    link=scholarship_data['link'],
                    requirements = scholarship_data['requirements'],
                    eligibility = scholarship_data['eligibility'],
                    source=source_name,
                    scrape_event=scrape_event 
                )
                scholarship.slug = unique_slug_generator(scholarship)
                new_scholarships.append(scholarship)
        
        if new_scholarships:
            Scholarship.objects.bulk_create(new_scholarships)
            created_count = len(new_scholarships)
        else:
            created_count = 0
        
        # Update scrape event
        scrape_event.scholarships_found = len(scraped_scholarships)
        scrape_event.scholarships_created = created_count
        scrape_event.scholarships_skipped = len(scraped_scholarships) - created_count
        scrape_event.mark_completed()
        
        # print(f"Created {created_count} new scholarships from {len(scraped_scholarships)} found")
        return created_count
        
    except Exception as e:
        scrape_event.mark_failed(str(e))
        raise




@shared_task
def scrape_scholarship_data():
    list_urls = [
        "https://www.scholarshipregion.com/category/undergraduate-scholarships/",
        # "https://www.scholarshipregion.com/category/postgraduate-scholarships/",
        # Add more list URLs as needed
    ]
    for url in list_urls:
        data = helpers.main_scholarship_scraper(url)
        data = data['scholarships']
        bulk_create(data, url, url)

@shared_task(bind=True)
def send_email_reminder(self):
    try:
        return ScholarshipEmailService.send_bulk_reminders()
    except Exception as e:
        raise self.retry(exc=e, countdown=300, max_retries=2)
    
@shared_task(bind=True)
def send_deadline_reminder(self):
    try:
        return ScholarshipEmailService.send_deadline_reminders()
    except Exception as e:
        raise self.retry(exc=e, countdown=300, max_retries=2)