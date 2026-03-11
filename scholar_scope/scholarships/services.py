# from datetime import timedelta
# from collections import defaultdict
# from django.utils import timezone
# from django.core.mail import EmailMultiAlternatives
# from django.template.loader import render_to_string
# from django.conf import settings
# import logging

# logger = logging.getLogger(__name__)


# class ScholarshipEmailService:

#     @staticmethod
#     def send_deadline_reminder(days_before_deadline=7):
#         """
#         Send reminders per user for all scholarships expiring in X days.
#         """
#         from .models import Application

#         # Target date (deadline)
#         target_date = timezone.now().date() + timedelta(days=days_before_deadline)

#         # Get applications that are pending AND scholarships expiring on target_date
#         applications = (
#             Application.objects.filter(
#                 status="PENDING",
#                 scholarship__end_date=target_date
#             )
#             .select_related("user", "scholarship")
#         )

#         # Group applications by user
#         user_applications = defaultdict(list)
#         for app in applications:
#             user_applications[app.user].append(app)

#         success_count = 0
#         total_count = len(user_applications)

#         # Send one email per user with all their scholarships
#         for user, apps in user_applications.items():
#             if ScholarshipEmailService.send_user_reminder(user, apps):
#                 success_count += 1

#         logger.info(f"Sent {success_count}/{total_count} user reminder emails")
#         return success_count, total_count
    
#     @staticmethod
#     def _build_scholarship_data(applications):
#         """Format scholarships for template rendering."""
#         scholarships_data = []

#         for app in applications:
#             scholarship = app.scholarship
#             days_remaining = (scholarship.end_date.date() - timezone.now().date()).days

#             scholarships_data.append({
#                 "title": scholarship.title,
#                 "deadline_date": scholarship.end_date.strftime("%B %d, %Y"),
#                 "award_amount": f"{scholarship.reward}" if scholarship.reward else "Amount varies",
#                 "application_date": app.submitted_at.strftime("%B %d, %Y"),
#                 "days_remaining": days_remaining,
#             })

#         return scholarships_data

#     @staticmethod
#     def send_user_reminder(user, applications):
#         """
#         Send one email reminder to a user with all their pending applications.
#         """
#         try:
#             scholarships_data = ScholarshipEmailService._build_scholarship_data(applications)

#             if not scholarships_data:
#                 logger.info(f"No pending applications for {user.email}, skipping reminder.")
#                 return False

#             context = {
#                 "user_name": user.get_full_name() or user.username,
#                 "scholarships": scholarships_data,
#                 "dashboard_url": f"{settings.SITE_URL}/dashboard/applications/",
#                 "organization_name": getattr(settings, "ORGANIZATION_NAME", "Your Organization"),
#                 "organization_address": getattr(settings, "ORGANIZATION_ADDRESS", ""),
#                 "user_email": user.email,
#                 "unsubscribe_url": f"{settings.SITE_URL}/unsubscribe/{user.id}/",
#                 "contact_url": f"{settings.SITE_URL}/contact/",
#                 "privacy_policy_url": f"{settings.SITE_URL}/privacy/",
#             }

#             # Render templates
#             html_content = render_to_string("emails/scholarship_reminder.html", context)
#             text_content = render_to_string("emails/scholarship_reminder.txt", context)

#             subject = f"Reminder: You have {len(scholarships_data)} pending scholarship application(s)"
#             from_email = settings.DEFAULT_FROM_EMAIL
#             to_email = [user.email]

#             msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
#             msg.attach_alternative(html_content, "text/html")
#             msg.send()

#             logger.info(f"Scholarship reminder sent to {user.email} for {len(scholarships_data)} applications")
#             return True

#         except Exception as e:
#             logger.error(f"Failed to send scholarship reminder to {user.email}: {str(e)}")
#             return False

#     @staticmethod
#     def send_bulk_reminders():
#         """
#         Group applications by user and send one email per user.
#         """
#         from django.contrib.auth import get_user_model
#         from .models import Application

#         User = get_user_model()
#         applications = Application.objects.filter(status="pending").select_related("user", "scholarship")

#         # Group applications by user
#         user_app_map = {}
#         for app in applications:
#             user_app_map.setdefault(app.user, []).append(app)

#         success_count = 0
#         total_count = len(user_app_map)

#         for user, apps in user_app_map.items():
#             if ScholarshipEmailService.send_user_reminder(user, apps):
#                 success_count += 1

#         logger.info(f"Sent {success_count}/{total_count} user reminder emails")
#         return success_count, total_count

# scholarships/services.py
from datetime import timedelta
from collections import defaultdict
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# ── Single source of truth for application status values ─────────────────────
# Your model uses uppercase choices ("PENDING", "APPROVED", etc.).
# Both tasks now go through this service so the casing is always consistent.
PENDING_STATUS = "PENDING"


class ScholarshipEmailService:

    # ── Shared internals ──────────────────────────────────────────────────────

    @staticmethod
    def _send(user, subject, html_template, text_template, context):
        """
        Low-level send helper. Returns True on success, False on failure.
        Centralises logging and exception handling so the public methods
        stay clean.
        """
        try:
            context.setdefault("user_name",  user.get_full_name() or user.username)
            context.setdefault("user_email", user.email)
            context.setdefault("dashboard_url",
                f"{settings.SITE_URL}/dashboard/applications/")
            context.setdefault("unsubscribe_url",
                f"{settings.SITE_URL}/unsubscribe/{user.id}/")
            context.setdefault("contact_url",     f"{settings.SITE_URL}/contact/")
            context.setdefault("privacy_policy_url", f"{settings.SITE_URL}/privacy/")
            context.setdefault("organization_name",
                getattr(settings, "ORGANIZATION_NAME", "ScholarScope"))
            context.setdefault("organization_address",
                getattr(settings, "ORGANIZATION_ADDRESS", ""))

            html_content = render_to_string(html_template, context)
            text_content = render_to_string(text_template, context)

            msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            logger.info("Email '%s' sent to %s", subject[:60], user.email)
            return True

        except Exception as exc:
            logger.error(
                "Failed to send '%s' to %s: %s", subject[:60], user.email, exc,
                exc_info=True,
            )
            return False

    @staticmethod
    def _build_scholarship_data(applications):
        """Format application records for template rendering."""
        data = []
        today = timezone.now().date()
        for app in applications:
            s = app.scholarship
            end = s.end_date.date() if hasattr(s.end_date, "date") else s.end_date
            data.append({
                "title":            s.title,
                "deadline_date":    end.strftime("%B %d, %Y") if end else "TBA",
                "award_amount":     str(s.reward) if s.reward else "Amount varies",
                "application_date": app.submitted_at.strftime("%B %d, %Y"),
                "days_remaining":   (end - today).days if end else None,
                "apply_url":        s.link or "",
                "is_renewal":       False,
            })
        return data

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def send_user_reminder(user, applications):
        """One deadline-reminder digest email for a single user."""
        scholarships_data = ScholarshipEmailService._build_scholarship_data(
            applications
        )
        if not scholarships_data:
            logger.info("No scholarship data for %s, skipping.", user.email)
            return False

        subject = (
            f"Reminder: {len(scholarships_data)} scholarship deadline"
            f"{'s' if len(scholarships_data) > 1 else ''} coming up"
        )
        return ScholarshipEmailService._send(
            user, subject,
            "emails/scholarship_reminder.html",
            "emails/scholarship_reminder.txt",
            {"scholarships": scholarships_data},
        )

    @staticmethod
    def send_renewal_email(user, scholarships_data):
        """
        Notify a watcher that one or more recurring scholarships have reopened.
        Uses a dedicated renewal template with slightly different copy
        ("re-opened" vs "deadline approaching").
        """
        if not scholarships_data:
            return False

        subject = (
            f"{'A scholarship' if len(scholarships_data) == 1 else str(len(scholarships_data)) + ' scholarships'}"
            f" you're watching {'has' if len(scholarships_data) == 1 else 'have'} reopened!"
        )
        return ScholarshipEmailService._send(
            user, subject,
            "emails/scholarship_renewal.html",   # separate template — see below
            "emails/scholarship_renewal.txt",
            {"scholarships": scholarships_data},
        )

    @staticmethod
    def send_deadline_reminder(days_before_deadline=7):
        """
        Send reminders per user for all scholarships expiring in exactly
        `days_before_deadline` days.
        """
        from .models import Application

        target_date = timezone.now().date() + timedelta(days=days_before_deadline)

        applications = (
            Application.objects
            .filter(status=PENDING_STATUS, scholarship__end_date=target_date)
            .select_related("user", "scholarship")
        )

        user_applications = defaultdict(list)
        for app in applications:
            user_applications[app.user].append(app)

        success = sum(
            ScholarshipEmailService.send_user_reminder(user, apps)
            for user, apps in user_applications.items()
        )
        total = len(user_applications)
        logger.info("Deadline reminders (%dd): %d/%d sent", days_before_deadline, success, total)
        return success, total

    @staticmethod
    def send_bulk_reminders():
        """
        Send one digest email per user listing ALL their pending applications,
        regardless of deadline proximity. Useful as a weekly catch-all.
        """
        from .models import Application

        applications = (
            Application.objects
            .filter(status=PENDING_STATUS)   # ← consistent with send_deadline_reminder
            .select_related("user", "scholarship")
        )

        user_app_map = defaultdict(list)
        for app in applications:
            user_app_map[app.user].append(app)

        success = sum(
            ScholarshipEmailService.send_user_reminder(user, apps)
            for user, apps in user_app_map.items()
        )
        total = len(user_app_map)
        logger.info("Bulk reminders: %d/%d sent", success, total)
        return success, total