# import sys
# import multiprocessing
# from django.core.management.base import BaseCommand
# from django.utils import timezone

# class Command(BaseCommand):
#     help = 'Run scheduled tasks outside Celery Beat via GitHub Actions'

#     def add_arguments(self, parser):
#         parser.add_argument(
#             'task', 
#             nargs='?', 
#             default='all',
#             choices=['reminders', 'deadlines', 'renewals', 'outdated', 'deduplicate', 'scrape', 'all'],
#             help='Specific task to run'
#         )

#     def handle(self, *args, **options):
#         task = options['task']
        
#         if task in ('reminders', 'all'):
#             self.stdout.write('Starting bulk reminders...')
#             from scholarships.tasks import send_email_reminder
#             # Call the task synchronously, bypassing Celery's .delay()
#             result = send_email_reminder()
#             self.stdout.write(self.style.SUCCESS(f'Bulk reminders complete: {result}'))

#         if task in ('deadlines', 'all'):
#             self.stdout.write('Starting deadline reminders...')
#             from scholarships.tasks import send_deadline_reminder
#             res_7 = send_deadline_reminder(days_before=7)
#             res_3 = send_deadline_reminder(days_before=3)
#             self.stdout.write(self.style.SUCCESS(f'Deadline reminders complete | 7-day: {res_7} | 3-day: {res_3}'))

#         if task in ('renewals', 'all'):
#             self.stdout.write('Starting renewal notifications...')
#             from scholarships.tasks import send_weekly_renewal_notifications
#             result = send_weekly_renewal_notifications()
#             self.stdout.write(self.style.SUCCESS(f'Renewal notifications complete: {result}'))

#         if task in ('outdated', 'all'):
#             self.stdout.write('Running outdated scholarship cleanup...')
#             from scholarships.tasks import outdated_scholarships
#             result = outdated_scholarships()
#             self.stdout.write(self.style.SUCCESS(f'Marked {result} scholarships as inactive.'))

#         if task in ('deduplicate', 'all'):
#             self.stdout.write('Running semantic deduplication...')
#             from scholarships.tasks import remove_semantic_duplicates
#             result = remove_semantic_duplicates(threshold=0.95)
#             self.stdout.write(self.style.SUCCESS(f'Deduplication complete: {result}'))

#         if task in ('scrape', 'all'):
#             self.stdout.write('Starting Scrapy spiders...')
#             from scholarships.models import SiteConfig
#             from scholarships.tasks import _run_spider_process
#             from django.db import connection

#             sources = SiteConfig.objects.filter(active=True)
#             for site in sources:
#                 p = multiprocessing.Process(
#                     target=_run_spider_process,
#                     args=(site.id, None)
#                 )
#                 p.start()
#                 p.join()
                
#                 if p.exitcode != 0:
#                     self.stderr.write(self.style.ERROR(f'Spider crashed for: {site.name} (Code: {p.exitcode})'))
#                 else:
#                     # Update timestamp on success since we aren't using the scrape_site task wrapper
#                     site.last_scraped = timezone.now()
#                     connection.close()
#                     site.save(update_fields=["last_scraped"])
#                     self.stdout.write(self.style.SUCCESS(f'Successfully scraped: {site.name}'))

# scholarships/management/commands/run_scheduled_tasks.py
#
# Runs all scheduled tasks synchronously — designed for GitHub Actions.
# Bypasses Celery task wrappers entirely and calls service/logic directly.
# This avoids the bind=True / self argument problem.

import sys
import multiprocessing
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Run scheduled tasks outside Celery Beat via GitHub Actions'

    def add_arguments(self, parser):
        parser.add_argument(
            'task',
            nargs='?',
            default='all',
            choices=[
                'reminders', 'deadlines', 'renewals',
                'outdated', 'deduplicate', 'scrape', 'all'
            ],
            help='Specific task to run (default: all)',
        )

    def handle(self, *args, **options):
        task = options['task']

        # ── 1. Bulk reminders ─────────────────────────────────────────────────
        if task in ('reminders', 'all'):
            self.stdout.write('Starting bulk reminders...')
            try:
                from scholarships.services import ScholarshipEmailService
                success, total = ScholarshipEmailService.send_bulk_reminders()
                self.stdout.write(self.style.SUCCESS(
                    f'Bulk reminders complete: {success}/{total} sent'
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Bulk reminders failed: {e}'))

        # ── 2. Deadline reminders ─────────────────────────────────────────────
        if task in ('deadlines', 'all'):
            self.stdout.write('Starting deadline reminders...')
            try:
                from scholarships.services import ScholarshipEmailService
                s7, t7 = ScholarshipEmailService.send_deadline_reminder(
                    days_before_deadline=7
                )
                s3, t3 = ScholarshipEmailService.send_deadline_reminder(
                    days_before_deadline=3
                )
                self.stdout.write(self.style.SUCCESS(
                    f'Deadline reminders complete | 7-day: {s7}/{t7} | 3-day: {s3}/{t3}'
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Deadline reminders failed: {e}'))

        # ── 3. Renewal notifications ──────────────────────────────────────────
        if task in ('renewals', 'all'):
            self.stdout.write('Starting renewal notifications...')
            try:
                from collections import defaultdict
                from scholarships.models import WatchedScholarship, Scholarship
                from scholarships.services import ScholarshipEmailService

                seven_days_ago = timezone.now() - timezone.timedelta(days=7)
                current_year   = timezone.now().year

                renewed = Scholarship.objects.filter(
                    status='active',
                    is_recurring=True,
                    last_renewed_at__gte=seven_days_ago,
                )

                if not renewed.exists():
                    self.stdout.write('No renewals this week.')
                else:
                    user_renewals = defaultdict(list)

                    for scholarship in renewed:
                        watchers = (
                            WatchedScholarship.objects
                            .filter(scholarship=scholarship)
                            .exclude(notified_for_year=current_year)
                            .select_related('user')
                        )
                        for watch in watchers:
                            if watch.user.email:
                                user_renewals[watch.user].append((scholarship, watch))

                    emails_sent = emails_failed = 0

                    for user, pairs in user_renewals.items():
                        scholarships_data = [
                            {
                                'title':            s.title,
                                'deadline_date':    s.end_date.strftime('%B %d, %Y') if s.end_date else 'TBA',
                                'award_amount':     str(s.reward) if s.reward else 'Amount varies',
                                'application_date': s.last_renewed_at.strftime('%B %d, %Y'),
                                'days_remaining':   (
                                    (s.end_date - timezone.now().date()).days
                                    if s.end_date else None
                                ),
                                'apply_url':  s.link or '',
                                'is_renewal': True,
                            }
                            for s, _ in pairs
                        ]

                        if ScholarshipEmailService.send_renewal_email(user, scholarships_data):
                            watch_ids = [w.id for _, w in pairs]
                            WatchedScholarship.objects.filter(
                                id__in=watch_ids
                            ).update(notified_for_year=current_year)
                            emails_sent += 1
                        else:
                            emails_failed += 1

                    self.stdout.write(self.style.SUCCESS(
                        f'Renewal notifications complete: {emails_sent} sent, {emails_failed} failed'
                    ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Renewal notifications failed: {e}'))

        # ── 4. Outdated scholarship cleanup ───────────────────────────────────
        if task in ('outdated', 'all'):
            self.stdout.write('Running outdated scholarship cleanup...')
            try:
                from scholarships.models import Scholarship
                cutoff = timezone.now().date()
                updated = Scholarship.objects.filter(
                    end_date__lt=cutoff,
                    active=True,
                    is_recurring=False,
                ).update(active=False)
                self.stdout.write(self.style.SUCCESS(
                    f'Marked {updated} scholarships as inactive.'
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Cleanup failed: {e}'))

        # ── 5. Semantic deduplication ─────────────────────────────────────────
        if task in ('deduplicate', 'all'):
            self.stdout.write('Running semantic deduplication...')
            try:
                # Call the underlying logic directly if you have a service method,
                # otherwise call .run() on the task to bypass bind=True:
                from scholarships.tasks import remove_semantic_duplicates
                # .run() calls the function body directly without Celery context
                result = remove_semantic_duplicates.run(threshold=0.95)
                self.stdout.write(self.style.SUCCESS(
                    f'Deduplication complete: {result}'
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Deduplication failed: {e}'))

        # ── 6. Scrapy spiders ─────────────────────────────────────────────────
        if task in ('scrape', 'all'):
            self.stdout.write('Starting Scrapy spiders...')
            try:
                from scholarships.models import SiteConfig
                from scholarships.tasks import _run_spider_process
                from django.db import connection

                sources = SiteConfig.objects.filter(active=True)

                if not sources.exists():
                    self.stdout.write('No active sources configured.')
                else:
                    for site in sources:
                        self.stdout.write(f'Scraping: {site.name}...')
                        p = multiprocessing.Process(
                            target=_run_spider_process,
                            args=(site.id, None),
                        )
                        p.start()
                        p.join()

                        if p.exitcode != 0:
                            self.stderr.write(self.style.ERROR(
                                f'Spider crashed for: {site.name} (exit code: {p.exitcode})'
                            ))
                        else:
                            # Close the DB connection before saving —
                            # the subprocess may have left it in a bad state
                            connection.close()
                            site.refresh_from_db()
                            site.last_scraped = timezone.now()
                            site.save(update_fields=['last_scraped'])
                            self.stdout.write(self.style.SUCCESS(
                                f'Successfully scraped: {site.name}'
                            ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Scraping failed: {e}'))
                sys.exit(1)