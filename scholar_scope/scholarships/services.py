# emails/services.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
from collections import defaultdict
logger = logging.getLogger(__name__)

# class ScholarshipEmailService:
    
#     @staticmethod
#     def send_scholarship_reminder(user, scholarship, application):
#         """
#         Send scholarship application reminder email
#         """
#         try:
#             # Calculate days remaining until deadline
#             days_remaining = (scholarship.end_date.date() - timezone.now().date()).days
            
#             # Prepare context for the email template
#             context = {
#                 'user_name': user.get_full_name() or user.username,
#                 'scholarship_name': scholarship.title,
#                 'deadline_date': scholarship.end_date.strftime('%B %d, %Y'),
#                 'award_amount': f"{scholarship.reward}" if scholarship.reward else "Amount varies",
#                 'application_date': application.submitted_at.strftime('%B %d, %Y'),
#                 'days_remaining': days_remaining,
#                 'dashboard_url': f"{settings.SITE_URL}/dashboard/applications/",
#                 'organization_name': getattr(settings, 'ORGANIZATION_NAME', 'Your Organization'),
#                 'organization_address': getattr(settings, 'ORGANIZATION_ADDRESS', ''),
#                 'user_email': user.email,
#                 'unsubscribe_url': f"{settings.SITE_URL}/unsubscribe/{user.id}/",
#                 'contact_url': f"{settings.SITE_URL}/contact/",
#                 'privacy_policy_url': f"{settings.SITE_URL}/privacy/",
#             }
            
#             # Render the HTML template
#             html_content = render_to_string('emails/scholarship_reminder.html', context)
            
#             # Create plain text version (optional but recommended)
#             text_content = f"""
#             Hello {context['user_name']},

#             This is a reminder about your pending scholarship application:

#             Scholarship: {context['scholarship_name']}
#             Deadline: {context['deadline_date']} ({days_remaining} days remaining)
#             Award Amount: {context['award_amount']}
#             Applied On: {context['application_date']}

#             Please visit {context['dashboard_url']} to check your application status.

#             Best regards,
#             The Scholarship Team
#             """
            
#             # Create email message
#             subject = f"Reminder: {scholarship.title} Application Deadline Approaching"
#             from_email = settings.DEFAULT_FROM_EMAIL
#             to_email = [user.email]
            
#             msg = EmailMultiAlternatives(
#                 subject=subject,
#                 body=text_content,
#                 from_email=from_email,
#                 to=to_email
#             )
            
#             # Attach HTML version
#             msg.attach_alternative(html_content, "text/html")
            
#             # Send the email
#             msg.send()
            
#             logger.info(f"Scholarship reminder sent to {user.email} for {scholarship.title}")
#             return True
            
#         except Exception as e:
#             logger.error(f"Failed to send scholarship reminder to {user.email}: {str(e)}")
#             return False
    
#     @staticmethod
#     def send_bulk_reminders():
#         """
#         Send reminders to all users with applications approaching deadline
#         """
#         from django.contrib.auth import get_user_model
#         from .models import Application, Scholarship
        
#         User = get_user_model()
#         applications = Application.objects.filter(status='pending').select_related('user', 'scholarship')
#         print(len(applications))
#             # # Calculate the target date
#             # target_date = timezone.now().date() + timedelta(days=days_before_deadline)
            
#             # # Get applications with deadlines approaching
#             # applications = Application.objects.filter(
#             #     status='PENDING',
#             #     scholarship__end_date=target_date
#             # ).select_related('user', 'scholarship')

#         success_count = 0
#         total_count = applications.count()
        
#         for application in applications:
#             if ScholarshipEmailService.send_scholarship_reminder(
#                 application.user, 
#                 application.scholarship, 
#                 application
#             ):
#                 success_count += 1
        
#         logger.info(f"Sent {success_count}/{total_count} scholarship reminder emails")
#         return success_count, total_count
    
    # def send_deadline_reminder(days_before_deadline=7):
    #     target_date = timezone.now().date() + timedelta(days=days_before_deadline)
    #     from .models import Application, Scholarship
    #     applications = Application.objects.filter(status='PENDING', scholarship__end_date=target_date).select_related('user', 'scholarship')

    #     success_count = 0
    #     total_count = applications.count()
        
    #     for application in applications:
    #         if ScholarshipEmailService.send_scholarship_reminder(
    #             application.user, 
    #             application.scholarship, 
    #             application
    #         ):
    #             success_count += 1
        
    #     logger.info(f"Sent {success_count}/{total_count} scholarship reminder emails")
    #     return success_count, total_count


from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ScholarshipEmailService:

    @staticmethod
    def send_deadline_reminder(days_before_deadline=7):
        """
        Send reminders per user for all scholarships expiring in X days.
        """
        from .models import Application

        # Target date (deadline)
        target_date = timezone.now().date() + timedelta(days=days_before_deadline)

        # Get applications that are pending AND scholarships expiring on target_date
        applications = (
            Application.objects.filter(
                status="PENDING",
                scholarship__end_date=target_date
            )
            .select_related("user", "scholarship")
        )

        # Group applications by user
        user_applications = defaultdict(list)
        for app in applications:
            user_applications[app.user].append(app)

        success_count = 0
        total_count = len(user_applications)

        # Send one email per user with all their scholarships
        for user, apps in user_applications.items():
            if ScholarshipEmailService.send_user_reminder(user, apps):
                success_count += 1

        logger.info(f"Sent {success_count}/{total_count} user reminder emails")
        return success_count, total_count
    
    @staticmethod
    def _build_scholarship_data(applications):
        """Format scholarships for template rendering."""
        scholarships_data = []

        for app in applications:
            scholarship = app.scholarship
            days_remaining = (scholarship.end_date.date() - timezone.now().date()).days

            scholarships_data.append({
                "title": scholarship.title,
                "deadline_date": scholarship.end_date.strftime("%B %d, %Y"),
                "award_amount": f"{scholarship.reward}" if scholarship.reward else "Amount varies",
                "application_date": app.submitted_at.strftime("%B %d, %Y"),
                "days_remaining": days_remaining,
            })

        return scholarships_data

    @staticmethod
    def send_user_reminder(user, applications):
        """
        Send one email reminder to a user with all their pending applications.
        """
        try:
            scholarships_data = ScholarshipEmailService._build_scholarship_data(applications)

            if not scholarships_data:
                logger.info(f"No pending applications for {user.email}, skipping reminder.")
                return False

            context = {
                "user_name": user.get_full_name() or user.username,
                "scholarships": scholarships_data,
                "dashboard_url": f"{settings.SITE_URL}/dashboard/applications/",
                "organization_name": getattr(settings, "ORGANIZATION_NAME", "Your Organization"),
                "organization_address": getattr(settings, "ORGANIZATION_ADDRESS", ""),
                "user_email": user.email,
                "unsubscribe_url": f"{settings.SITE_URL}/unsubscribe/{user.id}/",
                "contact_url": f"{settings.SITE_URL}/contact/",
                "privacy_policy_url": f"{settings.SITE_URL}/privacy/",
            }

            # Render templates
            html_content = render_to_string("emails/scholarship_reminder.html", context)
            text_content = render_to_string("emails/scholarship_reminder.txt", context)

            subject = f"Reminder: You have {len(scholarships_data)} pending scholarship application(s)"
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [user.email]

            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            logger.info(f"Scholarship reminder sent to {user.email} for {len(scholarships_data)} applications")
            return True

        except Exception as e:
            logger.error(f"Failed to send scholarship reminder to {user.email}: {str(e)}")
            return False

    @staticmethod
    def send_bulk_reminders():
        """
        Group applications by user and send one email per user.
        """
        from django.contrib.auth import get_user_model
        from .models import Application

        User = get_user_model()
        applications = Application.objects.filter(status="pending").select_related("user", "scholarship")

        # Group applications by user
        user_app_map = {}
        for app in applications:
            user_app_map.setdefault(app.user, []).append(app)

        success_count = 0
        total_count = len(user_app_map)

        for user, apps in user_app_map.items():
            if ScholarshipEmailService.send_user_reminder(user, apps):
                success_count += 1

        logger.info(f"Sent {success_count}/{total_count} user reminder emails")
        return success_count, total_count
