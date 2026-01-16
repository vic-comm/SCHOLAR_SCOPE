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



# from celery import shared_task
# from django.conf import settings
# from .models import Scholarship
# import openai 
# import json

# @shared_task
# def process_scholarship_with_ai(scholarship_id):
#     try:
#         scholarship = Scholarship.objects.get(id=scholarship_id)
        
#         # Combine all text for the AI to read
#         full_text = f"""
#         Title: {scholarship.title}
#         Desc: {scholarship.description}
#         Elig: {scholarship.eligibility}
#         Reqs: {scholarship.requirements}
#         """

#         # 1. The Prompt
#         prompt = f"""
#         You are a data cleaner for a scholarship database.
#         Analyze the text below. 
        
#         Task 1: Extract 'deadline' (YYYY-MM-DD), 'country' (ISO code), and 'education_level'.
#         Task 2: Summarize 'eligibility' and 'requirements' into clean bullet points.
#         Task 3: Verify if this is a legitimate scholarship. If yes, set 'is_valid' to true.

#         Input Text: {full_text[:3000]} 

#         Return ONLY raw JSON:
#         {{
#             "is_valid": true/false,
#             "deadline": "YYYY-MM-DD" or null,
#             "country": "String" or null,
#             "education_level": "Undergraduate" or "Postgraduate" or "PhD" or "Any",
#             "clean_eligibility": "String...",
#             "clean_requirements": "String..."
#         }}
#         """

#         # 2. Call AI API
#         response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo", # or generic equivalent
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0
#         )
        
#         # 3. Parse JSON
#         data = json.loads(response.choices[0].message.content)

#         # 4. Update Database
#         if data.get('is_valid'):
#             if data.get('deadline'): scholarship.deadline = data['deadline']
#             if data.get('country'): scholarship.country = data['country']
#             if data.get('education_level'): scholarship.education_level = data['education_level']
            
#             # Replace messy user text with AI cleaned text (Optional, based on preference)
#             if data.get('clean_eligibility'): scholarship.eligibility = data['clean_eligibility']
#             if data.get('clean_requirements'): scholarship.requirements = data['clean_requirements']
            
#             scholarship.status = 'VERIFIED' # <--- Auto-Verification!
#         else:
#             scholarship.status = 'REJECTED' # AI thinks it's spam/junk

#         scholarship.save()

#     except Scholarship.DoesNotExist:
#         pass
#     except Exception as e:
#         print(f"AI Processing Failed: {e}")