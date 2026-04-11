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
            choices=['reminders', 'deadlines', 'renewals', 'outdated', 'deduplicate', 'scrape', 'all'],
            help='Specific task to run'
        )

    def handle(self, *args, **options):
        task = options['task']
        
        if task in ('reminders', 'all'):
            self.stdout.write('Starting bulk reminders...')
            from scholarships.tasks import send_email_reminder
            # Call the task synchronously, bypassing Celery's .delay()
            result = send_email_reminder()
            self.stdout.write(self.style.SUCCESS(f'Bulk reminders complete: {result}'))

        if task in ('deadlines', 'all'):
            self.stdout.write('Starting deadline reminders...')
            from scholarships.tasks import send_deadline_reminder
            res_7 = send_deadline_reminder(days_before=7)
            res_3 = send_deadline_reminder(days_before=3)
            self.stdout.write(self.style.SUCCESS(f'Deadline reminders complete | 7-day: {res_7} | 3-day: {res_3}'))

        if task in ('renewals', 'all'):
            self.stdout.write('Starting renewal notifications...')
            from scholarships.tasks import send_weekly_renewal_notifications
            result = send_weekly_renewal_notifications()
            self.stdout.write(self.style.SUCCESS(f'Renewal notifications complete: {result}'))

        if task in ('outdated', 'all'):
            self.stdout.write('Running outdated scholarship cleanup...')
            from scholarships.tasks import outdated_scholarships
            result = outdated_scholarships()
            self.stdout.write(self.style.SUCCESS(f'Marked {result} scholarships as inactive.'))

        if task in ('deduplicate', 'all'):
            self.stdout.write('Running semantic deduplication...')
            from scholarships.tasks import remove_semantic_duplicates
            result = remove_semantic_duplicates(threshold=0.95)
            self.stdout.write(self.style.SUCCESS(f'Deduplication complete: {result}'))

        if task in ('scrape', 'all'):
            self.stdout.write('Starting Scrapy spiders...')
            from scholarships.models import SiteConfig
            from scholarships.tasks import _run_spider_process
            from django.db import connection

            sources = SiteConfig.objects.filter(active=True)
            for site in sources:
                p = multiprocessing.Process(
                    target=_run_spider_process,
                    args=(site.id, None)
                )
                p.start()
                p.join()
                
                if p.exitcode != 0:
                    self.stderr.write(self.style.ERROR(f'Spider crashed for: {site.name} (Code: {p.exitcode})'))
                else:
                    # Update timestamp on success since we aren't using the scrape_site task wrapper
                    site.last_scraped = timezone.now()
                    connection.close()
                    site.save(update_fields=["last_scraped"])
                    self.stdout.write(self.style.SUCCESS(f'Successfully scraped: {site.name}'))