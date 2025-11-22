from datetime import timedelta, time, datetime
from scholarships.services import ScholarshipEmailService
from django.core.mail import mail_admins
from django.core.management import BaseCommand
from django.utils import timezone
from django.utils.timezone import make_aware

from scholarships.models import Application, Scholarship, User

today = timezone.now()
tomorrow = today + timedelta(1)
today_start = make_aware(datetime.combine(today, time()))
today_end = make_aware(datetime.combine(tomorrow, time()))


class Command(BaseCommand):
    help = 'Sending scholarship reminder emails'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7,  help='Number of days before deadline to send reminder (default: 7)')


    def handle(self, *args, **options):
        days = options['days']
        self.send_bulk_reminders(days)

    def send_bulk_reminders(self, days):
        from scholarships.models import Application
        target_date = timedelta.now().date() + timedelta(days=days)
        applications = Application.objects.filter(scholarship__end_date=target_date).select_related('user', 'scholarship')
        if not applications.exists():
            self.stdout.write(
                self.style.WARNING(f'No applications found with deadline in {days} days')
            )
            return
        
        self.stdout.write(f'Found {applications.count()} applications with deadline on {target_date}')

        success_count, total_count = ScholarshipEmailService.send_bulk_reminders(days)
