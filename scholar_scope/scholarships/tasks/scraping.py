import sys
import os
import multiprocessing 
from celery import shared_task
from scrapy.crawler import CrawlerProcess
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from asgiref.sync import async_to_sync
import dateparser
from datetime import date
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Fixed — configure once at module level, reuse model
import google.generativeai as genai
import os

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
    from scholarships.models import SiteConfig
    sources = SiteConfig.objects.filter(active=True)
    for site in sources:
        scrape_site.delay(site_config_id=site.id)

@shared_task
def finalize_scrape_event(results, scrape_event_id):
    from scholarships.models import ScholarshipScrapeEvent, FailedScholarship
    event = ScholarshipScrapeEvent.objects.get(id=scrape_event_id)
    failed = FailedScholarship.objects.filter(scrape_event=event).exists()
    if failed:
        event.mark_partial("Some scholarships failed — see FailedScholarship table")
    return "Scrape event completed"

@shared_task
def send_weekly_renewal_notifications():
    from scholarships.models import WatchedScholarship, Scholarship
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    renewed_scholarships = Scholarship.objects.filter(
        status='active',
        is_recurring=True,
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
        ).exclude(notified_for_year__year=current_year).select_related('user')
        
        for watch in watchers:
            user = watch.user
            if not user.email: continue
            
            subject = f"Action Required: {scholarship.title} is Open!"
            message = (
                f"Hello {user.first_name},\n\n"
                f"The scholarship you are tracking, '{scholarship.title}', "
                f"has reopened for the new cycle.\n\n"
                f"Deadline: {scholarship.latest_deadline}\n"
                f"Apply: {scholarship.link}\n\n"
                f"Good luck!"
            )
            
            try:
                send_mail(subject, message, 'noreply@scholarscope.com', [user.email])
                
                watch.notified_for_year = timezone.now()
                watch.notified_for_year = current_year
                watch.save()
                emails_sent += 1
            except Exception as e:
                print(f"Error emailing user {user.id}: {e}")

    return f"Sent {emails_sent} renewal notifications."

@shared_task
def process_new_submission(submission_id):
    from scholarships.models import ScrapeSubmission, Scholarship, Application, Tag, Level
    from scholarscope_scrapers.scholarscope_scrapers.utils.quality import QualityCheck
    from scholarscope_scrapers.scholarscope_scrapers.utils.llm_engine import LLMEngine
    from scholarships.utils import ScholarshipExtractor
    
    try:
        sub = ScrapeSubmission.objects.get(id=submission_id)
        if sub.status != 'PENDING': return

        # 1. ── PRE-PROCESSING: Convert HTML to Dictionary if necessary ──
        working_data = dict(sub.raw_data) # Create a working copy
        text_for_llm = "" # Cache this in case the LLM needs to read it later

        if 'raw_html' in working_data:
            print(f"Submission {sub.id}: 'raw_html' detected. Running Extractor.")
            raw_html = working_data.pop('raw_html')
            extractor = ScholarshipExtractor(raw_html=raw_html, url=sub.link)
            text_for_llm = extractor.clean_text
            
            # Map the extracted fields into the dictionary
            working_data.update({
                'title': extractor.extract_title() or working_data.get('title'),
                'description': extractor.extract_description(),
                'reward': extractor.extract_reward(),
                'end_date': extractor.extract_date('end'),
                'start_date': extractor.extract_date('start'),
                'requirements': extractor.extract_requirements(),
                'eligibility': extractor.extract_eligibility(),
                'tags': extractor.extract_tags(),
                'level': extractor.extract_levels(), 
            })
            
            # Dates must be strings for the QualityCheck and JSON saving
            for date_field in ['end_date', 'start_date']:
                if isinstance(working_data.get(date_field), date):
                    working_data[date_field] = working_data[date_field].isoformat()
        else:
            # Manual Mode: Just use the highlighted text as the fallback context
            text_for_llm = str(working_data)

        # 2. ── EXISTING QUALITY CHECK ──
        quality_report = QualityCheck.get_quality_score(
            working_data, 
            critical_fields=['title', 'link', 'description', 'reward', 'eligibility', 'requirements']
        )
        
        if quality_report.get('is_garbage_content'):
            sub.status = 'REJECTED'
            sub.raw_data['rejection_reason'] = quality_report['critical_failures']
            sub.save()
            return

        llm_engine = LLMEngine()
        ai_data = {}
        is_valid_scholarship = False

        # 3. ── AI FALLBACK LOOP ──
        if QualityCheck.should_full_regenerate(quality_report):
            print(f"Submission {sub.id}: Poor parsing detected. Full AI Regeneration.")
            # Note: Using async_to_sync because LLMEngine is typically asynchronous
            ai_result = async_to_sync(llm_engine.extract_data)(text_for_llm, sub.link)
            
            if isinstance(ai_result, list) and len(ai_result) > 0:
                ai_data = ai_result[0]
                is_valid_scholarship = True
            else:
                sub.status = 'REJECTED'
                sub.raw_data['rejection_reason'] = "AI confirmed invalid content"
                sub.save()
                return

        elif len(quality_report['failed_fields']) > 0:
            print(f"Submission {sub.id}: Mostly good, recovering fields: {quality_report['failed_fields']}")
            recovered_data = async_to_sync(llm_engine.recover_specific_fields)(
                text_for_llm, 
                fields_to_fix=quality_report['failed_fields']
            )
            ai_data = {**working_data, **recovered_data}
            is_valid_scholarship = True
            
        else:
            print(f"Submission {sub.id}: High quality, auto-approving.")
            ai_data = working_data
            is_valid_scholarship = True

        # 4. ── DATABASE SAVING ──
        def safe_parse_date(d):
            if not d: return None
            if isinstance(d, str):
                parsed = dateparser.parse(d)
                return parsed.date() if parsed else None
            return d

        if is_valid_scholarship:
            tags_list = ai_data.get('tags', [])
            levels_list = ai_data.get('level', []) or ai_data.get('levels', [])
            
            scholarship, created = Scholarship.objects.update_or_create(
                link=sub.link,
                defaults={
                    'title': (ai_data.get('title') or "Unknown")[:500],
                    'description': ai_data.get('description', ''),
                    'eligibility': ai_data.get('eligibility', []), 
                    'requirements': ai_data.get('requirements', []),
                    'reward': ai_data.get('reward', '')[:1000],
                    'start_date': safe_parse_date(ai_data.get('start_date')),
                    'end_date': safe_parse_date(ai_data.get('end_date')),
                    'active': True 
                }
            )
            
            # Update Many-to-Many fields
            scholarship.level.clear() 
            for lvl_name in levels_list:
                if lvl_name:
                    level_obj, _ = Level.objects.get_or_create(name=str(lvl_name).strip().title())
                    scholarship.level.add(level_obj)

            scholarship.tags.clear() 
            for tag_name in tags_list:
                if tag_name:
                    tag_obj, _ = Tag.objects.get_or_create(name=str(tag_name).strip().title())
                    scholarship.tags.add(tag_obj)

            # Finalize submission status
            sub.scholarship = scholarship
            sub.status = 'APPROVED'
            
            # Remove raw_html from the DB to save massive amounts of Postgres storage space
            if 'raw_html' in ai_data: del ai_data['raw_html']
            sub.raw_data = ai_data 
            
            sub.save()
            
            # Ensure it shows up on the user's board
            Application.objects.get_or_create(
                user=sub.user, 
                scholarship=scholarship,
                defaults={'status': 'pending'}
            )

    except ScrapeSubmission.DoesNotExist:
        pass
    except Exception as e:
        print(f"CRITICAL ERROR in process_new_submission {submission_id}: {str(e)}")
        # Optionally mark as rejected on catastrophic failure
        sub.status = 'REJECTED'
        sub.raw_data['error'] = str(e)
        sub.save()
