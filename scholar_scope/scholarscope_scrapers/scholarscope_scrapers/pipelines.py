# scholarscope_scrapers/pipelines.py
import logging
from scrapy.exceptions import DropItem
import os
from itemadapter import ItemAdapter
from django.utils import timezone
from django.db import transaction
from scholarships.utils import generate_fingerprint
from scholarships.models import Scholarship, ScholarshipScrapeEvent, Tag, Level, ScholarshipCycle
from asgiref.sync import sync_to_async
from rapidfuzz import fuzz, utils
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

BULK_BATCH_SIZE = 100
FUZZ_THRESHOLD = 85
DOMAIN_FUZZ_LIMIT = 500
GLOBAL_FUZZ_LIMIT = 500

class ScholarshipPipeline:
    def __init__(self):
        self.items_processed = 0
        self.items_created = 0
        self.scrape_event = None
        self.existing_fingerprints = set()
        self.existing_titles = []

    def open_spider(self, spider):
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        
        if getattr(spider, "scrape_event_id", None):
            self.scrape_event = ScholarshipScrapeEvent.objects.get(id=spider.scrape_event_id)
            self.scrape_event.mark_retried()
        else:
            source_name = getattr(spider, "source_name", spider.name)
            source_url = getattr(spider, "list_url", None)
            if not source_url and hasattr(spider, 'site_config'):
                source_url = spider.site_config.list_url
            self.scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
                source_name=source_name,
                source_url=source_url,
            )
        self.existing_fingerprints = set(Scholarship.objects.values_list("fingerprint", flat=True))
        self.existing_titles = list(Scholarship.objects.order_by("-created_at").values_list("title", flat=True)[:100])

    
    async def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        title = adapter.get("title")
        link = adapter.get("link")
        fingerprint = generate_fingerprint(title, link)
        adapter['fingerprint'] = fingerprint

        if fingerprint in self.existing_fingerprints:
            raise DropItem(f"Duplicate by fingerprint: {title}")

        for old in self.existing_titles:
            if title == old: 
                raise DropItem(f"Duplicate by exact title: {title}")
            
            if abs(len(title) - len(old)) < 10:
                if fuzz.token_sort_ratio(title, old) >= 85:
                    raise DropItem(f"Duplicate by fuzzy title: {title}")

        deadline = adapter.get("end_date")
        if deadline and deadline < timezone.now().date():
            raise DropItem(f"Expired scholarship: {title}")

        await sync_to_async(self._save_scholarship)(adapter, spider.name)
        
        self.existing_fingerprints.add(fingerprint)
        self.items_created += 1
        
        return item

    def _save_scholarship(self, item, source_name):
        reqs = item.get('requirements', [])
        if isinstance(reqs, list): reqs = "\n".join(reqs)

        elig = item.get('eligibility', [])
        if isinstance(elig, list): elig = "\n".join(elig)

        tags_list = item.get('tags', [])
        levels_list = item.get('levels', [])

        try:
            with transaction.atomic():
                scholarship = Scholarship.objects.create(
                    title=item.get('title'),
                    start_date=item.get('start_date'),
                    end_date=item.get('end_date'),
                    description=item.get('description', ''),
                    reward=item.get('reward', ''),
                    link=str(item.get('link')),
                    requirements=reqs,
                    eligibility=elig,
                    source=source_name,
                    scrape_event=self.scrape_event,
                    fingerprint=item.get('fingerprint'),
                    scraped_at=item.get('scraped_at')
                )

                for tag_name in tags_list:
                    if tag_name and tag_name != "general":
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        scholarship.tags.add(tag)

                for level_name in levels_list:
                    if level_name and level_name != "unspecified":
                        level, _ = Level.objects.get_or_create(level=level_name)
                        scholarship.level.add(level)

        except Exception as e:
            logger.error(f"Failed to save {item.get('title')}: {e}")

    def close_spider(self, spider):
        if self.scrape_event:
            self.scrape_event.scholarships_found = spider.scraped_count
            self.scrape_event.scholarships_created = self.items_created
            self.scrape_event.scholarships_skipped = spider.scraped_count - self.items_created
            
            self.scrape_event.mark_completed()
            logger.info(f"Scrape finished. Created {self.items_created} items.")



class RenewalAndDuplicatePipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        title = adapter.get('title')
        link = adapter.get('link')
        stop_words = {'the', 'a', 'an', 'international', 'global', '2024', '2025', '2026'}
        words = title.lower().split()
        search_term = next((w for w in words if w not in stop_words), words[0])
        candidates = Scholarship.objects.filter(title__icontains=search_term)
        
        best_match = None
        best_score = 0
        norm_title_new = utils.default_process(title)

        for old in candidates:
            norm_title_old = utils.default_process(old.title)
            score = fuzz.token_set_ratio(norm_title_new, norm_title_old)
            if score > best_score:
                best_score = score
                best_match = old

        if best_match and best_score >= 90:
            
            if best_match.status == 'active':
                raise DropItem(f"Duplicate of active item {best_match.id} (Score: {best_score})")

            elif best_match.status == 'expired':
                
                last_deadline = best_match.end_date
                year_guess = last_deadline.year if last_deadline else (timezone.now().year - 1)
                
                ScholarshipCycle.objects.get_or_create(
                    scholarship=best_match,
                    batch_year=year_guess,
                    defaults={"deadline": last_deadline, "status": "expired"}
                )

                best_match.status = "active"
                best_match.is_recurring = True
                best_match.last_renewed_at = timezone.now()
                best_match.link = link 
                
                new_deadline = adapter.get('end_date')
                best_match.end_date = new_deadline
                best_match.save()
                raise DropItem(f"Handled as Renewal for ID {best_match.id}")
        return item

