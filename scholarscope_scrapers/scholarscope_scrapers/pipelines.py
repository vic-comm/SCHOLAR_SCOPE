# scholarscope_scrapers/pipelines.py
from django.utils import timezone
from scholarships.tasks import bulk_create 
import logging
from django.db import IntegrityError, transaction
from django.db.models import Q
from fuzzywuzzy import fuzz
from scrapy.exceptions import DropItem
import logging
from datetime import datetime
from dateutil import parser as date_parser
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Q
from rapidfuzz import fuzz
from scholarships.models import (
    Scholarship,
    ScholarshipScrapeEvent,
)
from scholarships.utils import generate_fingerprint

logger = logging.getLogger(__name__)

BULK_BATCH_SIZE = 100
FUZZ_THRESHOLD = 85
DOMAIN_FUZZ_LIMIT = 500
GLOBAL_FUZZ_LIMIT = 500

class ScholarshipPipeline:

    def open_spider(self, spider):
        self.scraped_items = []
        source_name = getattr(spider, "source_name", spider.name)
        source_url = getattr(spider, "list_url", None)

        
        if getattr(spider, "scrape_event_id", None):
            # ✅ reuse existing event
            self.scrape_event = ScholarshipScrapeEvent.objects.get(id=spider.scrape_event_id)
            self.scrape_event.mark_retried()
        else:
            # ✅ create new event
            source_name = getattr(spider, "source_name", spider.name)
            source_url = getattr(spider, "list_url", None)
            self.scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
                source_name=source_name,
                source_url=source_url,
            )

    def process_item(self, item, spider):

        title = item.get("title")
        link = item.get("link")
        fingerprint = generate_fingerprint(title, link)
        item['fingerprint'] = fingerprint

        # ✅ 1. Fingerprint duplicate check
        if Scholarship.objects.filter(fingerprint=fingerprint).exists():
            raise DropItem(f"Duplicate by fingerprint: {title}")

        # ✅ 2. Fuzzy title similarity check
        recent_titles = Scholarship.objects.values_list("title", flat=True).order_by("-created_at")[:50]
        for old in recent_titles:
            if fuzz.token_sort_ratio(title, old) >= 85:
                raise DropItem(f"Duplicate by fuzzy title: {title}")

        # ✅ 3. Skip expired scholarships
        deadline = item.get("end_date")
        if deadline and deadline < timezone.now().date():
            raise DropItem(f"Expired scholarship: {title}")
        
        self.scraped_items.append(item)
        return item

    def close_spider(self, spider):
        if not self.scraped_items:
            logger.warning(f"No scholarships scraped for {spider.name}")
            self.scrape_event.mark_completed()
            return

        try:
            created_count = bulk_create(
                {entry["title"]: entry for entry in self.scraped_items},
                source_name=spider.name,
                source_url=getattr(spider, "list_url", None),
                scrape_event=self.scrape_event
            )
            logger.info(f"✅ {created_count} scholarships saved for {spider.name}")
        except Exception as e:
            logger.error(f"Failed to save scholarships: {e}")
            self.scrape_event.mark_failed(str(e))



# def normalize_title(title):
#     if not title:
#         return ""
#     return " ".join(title.split()).strip().lower()


# def extract_domain(url):
#     try:
#         from urllib.parse import urlparse
#         parsed = urlparse(url)
#         return parsed.netloc.lower()
#     except Exception:
#         return ""


# def parse_date_maybe(date_val):
#     if not date_val:
#         return None
#     if hasattr(date_val, "date"):
#         try:
#             return date_val.date()
#         except Exception:
#             pass
#     s = str(date_val).strip()
#     if not s:
#         return None
#     s = s.lower()
#     for prefix in ["on ", "by ", "until ", "closing date:", "deadline:"]:
#         if s.startswith(prefix):
#             s = s[len(prefix):].strip()
#     try:
#         dt = date_parser.parse(s, fuzzy=True, dayfirst=True)
#         return dt.date()
#     except Exception:
#         return None


# class ScholarshipPipeline:
#     def open_spider(self, spider):
#         self.scraped_items = []
#         self.failed_items = []
#         self.counters = {
#             "processed": 0,
#             "duplicates": 0,
#             "expired": 0,
#             "saved": 0,
#             "failed": 0,
#             "invalid": 0,
#             "renewals": 0,
#         }
#         source_name = getattr(spider, "source_name", spider.name)
#         source_url = getattr(spider, "list_url", None)
#         self.scrape_event = ScholarshipScrapeEvent.objects.create_scrape_event(
#             source_name=source_name,
#             source_url=source_url,
#         )
#         logger.info(f"Opened scrape event {self.scrape_event.id} for {source_name}")

#     def _validate_item(self, raw_item):
#         title = raw_item.get("title")
#         link = raw_item.get("link")
#         if not title or not title.strip():
#             return None, "Missing title"
#         if not link or not str(link).strip():
#             return None, "Missing link/URL"

#         title_clean = " ".join(title.split()).strip()
#         link_clean = str(link).strip()
#         end_date = parse_date_maybe(raw_item.get("end_date"))
#         start_date = parse_date_maybe(raw_item.get("start_date"))
#         fingerprint = generate_fingerprint(title_clean, link_clean)

#         today = timezone.now().date()
#         status = "open"
#         if end_date and end_date < today:
#             status = "expired"

#         item = {
#             "title": title_clean,
#             "normalized_title": normalize_title(title_clean),
#             "description": raw_item.get("description") or "",
#             "reward": raw_item.get("reward") or "",
#             "link": link_clean,
#             "end_date": end_date,
#             "start_date": start_date,
#             "requirements": raw_item.get("requirements") or "",
#             "eligibility": raw_item.get("eligibility") or "",
#             "tags": raw_item.get("tags") or [],
#             "level": raw_item.get("level") or [],
#             "scraped_at": raw_item.get("scraped_at") or datetime.utcnow().isoformat(),
#             "fingerprint": fingerprint,
#             "status": status,
#             "source_name": getattr(self.scrape_event, "source_name", None),
#             "source_url": getattr(self.scrape_event, "source_url", None),
#             "domain": extract_domain(link_clean),
#         }
#         return item, None

#     def _is_duplicate_simple(self, validated_item):
#         fp = validated_item["fingerprint"]
#         if Scholarship.objects.filter(fingerprint=fp).exists():
#             return True, "fingerprint"

#         domain = validated_item.get("domain")
#         if domain:
#             domain_titles_qs = Scholarship.objects.filter(link__icontains=domain).values_list("title", flat=True)[:DOMAIN_FUZZ_LIMIT]
#             for old_title in domain_titles_qs:
#                 if fuzz.token_sort_ratio(validated_item["normalized_title"], normalize_title(old_title)) >= FUZZ_THRESHOLD:
#                     return True, "domain_fuzzy"

#         recent_titles = Scholarship.objects.values_list("title", flat=True).order_by("-created_at")[:GLOBAL_FUZZ_LIMIT]
#         for old_title in recent_titles:
#             if fuzz.token_sort_ratio(validated_item["normalized_title"], normalize_title(old_title)) >= FUZZ_THRESHOLD:
#                 return True, "global_fuzzy"
#         return False, None

#     def _attempt_renewal_attach(self, validated_item):
#         """
#         If a matching expired scholarship exists (same domain or similar title),
#         attach this posting as a new cycle, update parent scholarship, create diff,
#         notify watchers. Returns True if renewal detected and handled.
#         """
#         # Query best candidates: same domain expired entries
#         domain = validated_item.get("domain")
#         candidates = Scholarship.objects.none()
#         if domain:
#             candidates = Scholarship.objects.filter(source=validated_item.get("source_name"), status="expired", link__icontains=domain).order_by("-created_at")[:DOMAIN_FUZZ_LIMIT]
#         else:
#             candidates = Scholarship.objects.filter(source=validated_item.get("source_name"), status="expired").order_by("-created_at")[:DOMAIN_FUZZ_LIMIT]

#         # Expand with recent expired globally if domain misses
#         if not candidates.exists():
#             candidates = Scholarship.objects.filter(status="expired").order_by("-latest_deadline")[:GLOBAL_FUZZ_LIMIT]

#         for old in candidates:
#             title_score = fuzz.token_sort_ratio(validated_item["normalized_title"], normalize_title(old.title))
#             if title_score >= FUZZ_THRESHOLD:
#                 # renewal detected
#                 logger.info(f"Renewal detected: new='{validated_item['title']}' matches old='{old.title}' (score={title_score})")
#                 # Build diff
#                 diff = {}
#                 for fld in ("requirements", "eligibility", "reward", "description"):
#                     old_val = (getattr(old, fld) or "").strip()
#                     new_val = (validated_item.get(fld) or "").strip()
#                     if old_val != new_val:
#                         diff[fld] = {"old": old_val, "new": new_val}

#                 # Create ScholarshipCycle for this year
#                 year = (validated_item["end_date"].year if validated_item["end_date"] else timezone.now().year)
#                 ScholarshipCycle.objects.update_or_create(
#                     scholarship=old,
#                     year=year,
#                     defaults={
#                         "start_date": validated_item.get("start_date"),
#                         "end_date": validated_item.get("end_date"),
#                         "requirements": validated_item.get("requirements"),
#                         "eligibility": validated_item.get("eligibility"),
#                         "reward": validated_item.get("reward"),
#                         "description": validated_item.get("description"),
#                     },
#                 )

#                 # Log the renewal diff (if any)
#                 ScholarshipRenewalLog.objects.create(
#                     scholarship=old,
#                     diff_summary=diff,
#                     note=f"Detected renewal for year {year}",
#                 )

#                 # Update the parent scholarship record (reactivate + update latest fields)
#                 old.status = "open"
#                 old.latest_deadline = validated_item.get("end_date")
#                 old.requirements = validated_item.get("requirements") or old.requirements
#                 old.eligibility = validated_item.get("eligibility") or old.eligibility
#                 old.link = old.link or validated_item.get("link")
#                 old.last_seen = timezone.now()
#                 old.save(update_fields=["status", "latest_deadline", "requirements", "eligibility", "link", "last_seen"])

#                 # Notify watchers
#                 watchers = WatchedScholarship.objects.filter(scholarship=old, is_active=True).select_related("user")
#                 for w in watchers:
#                     # Avoid duplicate notify for same year
#                     notif_year = validated_item.get("end_date").year if validated_item.get("end_date") else timezone.now().year
#                     if w.notified_for_year != notif_year:
#                         try:
#                             send_user_notification(
#                                 w.user,
#                                 subject=f"{old.title} is now open for {notif_year}",
#                                 body=f"The scholarship '{old.title}' has reopened. Deadline: {validated_item.get('end_date')}\nLink: {validated_item.get('link')}"
#                             )
#                         except Exception as e:
#                             logger.exception(f"Failed to notify user {w.user.id}: {e}")
#                         w.notified_for_year = notif_year
#                         w.save(update_fields=["notified_for_year"])

#                 self.counters["renewals"] += 1
#                 return True

#         return False

#     def process_item(self, item, spider):
#         self.counters["processed"] += 1
#         validated_item, err = self._validate_item(item)
#         if err:
#             self.counters["invalid"] += 1
#             logger.warning(f"Invalid item ({err}) from {getattr(spider, 'name', 'spider')}: {err} - {item.get('link')}")
#             self.failed_items.append({"item": item, "reason": err})
#             return None

#         # 1) Attempt renewal attach for expired candidates
#         # Only attempt renewal if we believe this posting could be a renewal (same source or expired candidates exist)
#         renewal_handled = False
#         try:
#             renewal_handled = self._attempt_renewal_attach(validated_item)
#         except Exception as e:
#             logger.exception(f"Error during renewal detection: {e}")

#         if renewal_handled:
#             # We handled this by updating an existing scholarship -> no new row required
#             return None

#         # 2) Duplicate detection
#         is_dup, reason = self._is_duplicate_simple(validated_item)
#         if is_dup:
#             self.counters["duplicates"] += 1
#             logger.info(f"Duplicate skipped ({reason}): {validated_item['title']}")
#             return None

#         # 3) expired bookkeeping
#         if validated_item["status"] == "expired":
#             self.counters["expired"] += 1
#             logger.info(f"Expired (kept as archived): {validated_item['title']}")

#         # 4) enqueue for saving
#         self.scraped_items.append(validated_item)
#         return validated_item

#     def _bulk_save_safe(self, items):
#         saved = 0
#         instances = []
#         for d in items:
#             inst = Scholarship(
#                 title=d["title"],
#                 normalized_title=d["normalized_title"],
#                 link=d["link"],
#                 fingerprint=d["fingerprint"],
#                 source_name=d.get("source_name"),
#                 source_url=d.get("source_url"),
#                 status="open" if d["status"] == "open" else "expired",
#                 latest_deadline=d.get("end_date"),
#                 requirements=d.get("requirements"),
#                 eligibility=d.get("eligibility"),
#                 created_at=datetime.utcnow(),
#             )
#             instances.append(inst)

#         for i in range(0, len(instances), BULK_BATCH_SIZE):
#             batch = instances[i : i + BULK_BATCH_SIZE]
#             try:
#                 Scholarship.objects.bulk_create(batch, ignore_conflicts=True)
#                 saved += len(batch)
#             except Exception as e:
#                 logger.exception(f"Bulk insert failed for batch starting at {i}: {e}. Falling back to per-item save.")
#                 for inst in batch:
#                     try:
#                         with transaction.atomic():
#                             inst.save()
#                             saved += 1
#                     except IntegrityError as ie:
#                         logger.warning(f"IntegrityError saving item {inst.title}: {ie}")
#                     except Exception as ie2:
#                         logger.exception(f"Failed saving item {inst.title}: {ie2}")
#         return saved

#     def close_spider(self, spider):
#         if not self.scraped_items and not self.failed_items:
#             logger.warning(f"No scholarships scraped for {spider.name}")
#             self.scrape_event.mark_completed(
#                 saved_count=0,
#                 processed=self.counters["processed"],
#                 duplicates=self.counters["duplicates"],
#                 invalid=self.counters["invalid"],
#                 expired=self.counters["expired"],
#                 failed=self.counters["failed"],
#                 renewals=self.counters["renewals"],
#             )
#             return

#         try:
#             saved_count = self._bulk_save_safe(self.scraped_items)
#             self.counters["saved"] = saved_count
#             logger.info(f"✅ {saved_count} scholarships saved for {spider.name}")
#             self.scrape_event.mark_completed(
#                 saved_count=saved_count,
#                 processed=self.counters["processed"],
#                 duplicates=self.counters["duplicates"],
#                 invalid=self.counters["invalid"],
#                 expired=self.counters["expired"],
#                 failed=len(self.failed_items),
#                 renewals=self.counters["renewals"],
#             )
#         except Exception as e:
#             logger.exception(f"Unexpected failure saving scholarships: {e}")
#             self.scrape_event.mark_failed(str(e))
#             send_admin_alert(
#                 subject=f"Scholarship pipeline failure for {spider.name}",
#                 body=f"Unexpected failure when saving scholarships: {e}"
#             )

#         if len(self.failed_items) > 0:
#             summary = {
#                 "source": getattr(spider, "name", None),
#                 "processed": self.counters["processed"],
#                 "saved": self.counters["saved"],
#                 "duplicates": self.counters["duplicates"],
#                 "invalid": self.counters["invalid"],
#                 "expired": self.counters["expired"],
#                 "failed_items_count": len(self.failed_items),
#                 "sample_failed": self.failed_items[:5],
#                 "renewals": self.counters["renewals"],
#             }
#             logger.warning(f"Some items failed during pipeline: {summary}")
#             if self.counters["saved"] < max(1, self.counters["processed"] // 10) or len(self.failed_items) > 10:
#                 send_admin_alert(
#                     subject=f"Scholarship pipeline warnings for {spider.name}",
#                     body=f"Pipeline summary: {summary}"
#                 )

