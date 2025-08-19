# emails/services.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class ScholarshipEmailService:
    
    @staticmethod
    def send_scholarship_reminder(user, scholarship, application):
        """
        Send scholarship application reminder email
        """
        try:
            # Calculate days remaining until deadline
            days_remaining = (scholarship.end_date - timezone.now().date()).days
            
            # Prepare context for the email template
            context = {
                'user_name': user.get_full_name() or user.username,
                'scholarship_name': scholarship.title,
                'deadline_date': scholarship.end_date.strftime('%B %d, %Y'),
                'award_amount': f"${scholarship.reward:,}" if scholarship.reward else "Amount varies",
                'application_date': application.started_at.strftime('%B %d, %Y'),
                'days_remaining': days_remaining,
                'dashboard_url': f"{settings.SITE_URL}/dashboard/applications/",
                'organization_name': getattr(settings, 'ORGANIZATION_NAME', 'Your Organization'),
                'organization_address': getattr(settings, 'ORGANIZATION_ADDRESS', ''),
                'user_email': user.email,
                'unsubscribe_url': f"{settings.SITE_URL}/unsubscribe/{user.id}/",
                'contact_url': f"{settings.SITE_URL}/contact/",
                'privacy_policy_url': f"{settings.SITE_URL}/privacy/",
            }
            
            # Render the HTML template
            html_content = render_to_string('templates/emails/scholarship_reminder.html', context)
            
            # Create plain text version (optional but recommended)
            text_content = f"""
            Hello {context['user_name']},

            This is a reminder about your pending scholarship application:

            Scholarship: {context['scholarship_name']}
            Deadline: {context['deadline_date']} ({days_remaining} days remaining)
            Award Amount: {context['award_amount']}
            Applied On: {context['application_date']}

            Please visit {context['dashboard_url']} to check your application status.

            Best regards,
            The Scholarship Team
            """
            
            # Create email message
            subject = f"Reminder: {scholarship.name} Application Deadline Approaching"
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [user.email]
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=to_email
            )
            
            # Attach HTML version
            msg.attach_alternative(html_content, "text/html")
            
            # Send the email
            msg.send()
            
            logger.info(f"Scholarship reminder sent to {user.email} for {scholarship.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send scholarship reminder to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_bulk_reminders():
        """
        Send reminders to all users with applications approaching deadline
        """
        from django.contrib.auth import get_user_model
        from .models import Application, Scholarship
        
        User = get_user_model()
        applications = Application.objects.filter(status='PENDING').select_related('user', 'scholarship')
       
            # # Calculate the target date
            # target_date = timezone.now().date() + timedelta(days=days_before_deadline)
            
            # # Get applications with deadlines approaching
            # applications = Application.objects.filter(
            #     status='PENDING',
            #     scholarship__end_date=target_date
            # ).select_related('user', 'scholarship')

        success_count = 0
        total_count = applications.count()
        
        for application in applications:
            if ScholarshipEmailService.send_scholarship_reminder(
                application.user, 
                application.scholarship, 
                application
            ):
                success_count += 1
        
        logger.info(f"Sent {success_count}/{total_count} scholarship reminder emails")
        return success_count, total_count
    
    def send_deadline_reminder(days_before_deadline=7):
        target_date = timezone.now().date() + timedelta(days=days_before_deadline)
        from .models import Application, Scholarship
        applications = Application.objects.filter(status='PENDING', scholarship__end_date=target_date).select_related('user', 'scholarship')

         # Get applications with deadlines approaching
        applications = Application.objects.filter(
            status='PENDING',
            scholarship__end_date=target_date
        ).select_related('user', 'scholarship')

        success_count = 0
        total_count = applications.count()
        
        for application in applications:
            if ScholarshipEmailService.send_scholarship_reminder(
                application.user, 
                application.scholarship, 
                application
            ):
                success_count += 1
        
        logger.info(f"Sent {success_count}/{total_count} scholarship reminder emails")
        return success_count, total_count