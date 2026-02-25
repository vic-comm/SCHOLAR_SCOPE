from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

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
