from datetime import timedelta
from collections import defaultdict
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging
from django.core.signing import Signer

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
            signer = Signer()
            secure_token = signer.sign(str(user.id))
            context.setdefault("user_name",  user.get_full_name() or user.username)
            context.setdefault("user_email", user.email)
            context.setdefault("dashboard_url",
                f"{settings.SITE_URL}/dashboard/applications/")
            context.setdefault("unsubscribe_url", f"{settings.SITE_URL}/unsubscribe/{secure_token}/")
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
            "emails/scholarship_renewal.html",   
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
            .filter(status=PENDING_STATUS, scholarship__end_date=target_date, user__receives_email_reminders=True)
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
            .filter(status=PENDING_STATUS, user__receives_email_reminders=True)   
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