# scholarships/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

logger = get_task_logger(__name__)

# ── Shared retry policy ───────────────────────────────────────────────────────
RETRY_KWARGS = dict(countdown=300, max_retries=3)


# ── 1. Bulk reminder — all users with ANY pending application ─────────────────
@shared_task(bind=True, name="scholarships.send_bulk_reminders")
def send_email_reminder(self):
    """
    Send one digest email per user listing all their pending applications.
    Triggered by Celery Beat on a schedule (e.g. every morning at 8am).
    """ 
    from scholarships.services import ScholarshipEmailService
    try:
        success, total = ScholarshipEmailService.send_bulk_reminders()
        logger.info("Bulk reminders: %d/%d sent", success, total)
        return {"success": success, "total": total}
    except Exception as exc:
        logger.error("Bulk reminder task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, **RETRY_KWARGS)


# ── 2. Deadline reminder — applications expiring in N days ────────────────────
@shared_task(bind=True, name="scholarships.send_deadline_reminders")
def send_deadline_reminder(self, days_before=7):
    """
    Send targeted reminders for scholarships whose deadline is exactly
    `days_before` days away. Run this task daily.
    """
    from scholarships.services import ScholarshipEmailService
    try:
        success, total = ScholarshipEmailService.send_deadline_reminder(
            days_before_deadline=days_before
        )
        logger.info(
            "Deadline reminders (%dd): %d/%d sent", days_before, success, total
        )
        return {"days_before": days_before, "success": success, "total": total}
    except Exception as exc:
        logger.error(
            "Deadline reminder task failed (days=%d): %s", days_before, exc,
            exc_info=True,
        )
        raise self.retry(exc=exc, **RETRY_KWARGS)


# ── 3. Weekly renewal notifications — recurring scholarships re-opened ────────
@shared_task(bind=True, name="scholarships.send_renewal_notifications")
def send_weekly_renewal_notifications(self):
    """
    For every recurring scholarship that renewed in the last 7 days, notify
    all watchers who haven't been notified yet this calendar year.

    Uses the same HTML email infrastructure as the deadline reminders so
    users get a consistent, branded experience.
    """
    from scholarships.models import WatchedScholarship, Scholarship
    from scholarships.services import ScholarshipEmailService

    try:
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        current_year   = timezone.now().year

        renewed = Scholarship.objects.filter(
            status="active",          # match your model's actual choice value
            is_recurring=True,
            last_renewed_at__gte=seven_days_ago,
        )

        if not renewed.exists():
            logger.info("Renewal notifications: no scholarships renewed this week")
            return {"emails_sent": 0, "reason": "no_renewals"}

        logger.info(
            "Renewal notifications: processing %d renewed scholarships",
            renewed.count(),
        )

        # Collect per-user renewals so we send ONE email per user, not one
        # per scholarship — same pattern as the deadline reminder service.
        from collections import defaultdict
        user_renewals = defaultdict(list)   # user → [scholarship, ...]

        for scholarship in renewed:
            # Only notify watchers not yet notified this calendar year
            watchers = (
                WatchedScholarship.objects
                .filter(scholarship=scholarship)
                .exclude(notified_for_year=current_year)   # int field, see model note
                .select_related("user")
            )
            for watch in watchers:
                if watch.user.email:
                    user_renewals[watch.user].append((scholarship, watch))

        emails_sent  = 0
        emails_failed = 0

        for user, pairs in user_renewals.items():
            scholarships_data = [
                {
                    "title":            s.title,
                    "deadline_date":    s.end_date.strftime("%B %d, %Y") if s.end_date else "TBA",
                    "award_amount":     str(s.reward) if s.reward else "Amount varies",
                    # renewal emails don't have an application date — use re-open date
                    "application_date": s.last_renewed_at.strftime("%B %d, %Y"),
                    "days_remaining":   (
                        (s.end_date - timezone.now().date()).days
                        if s.end_date else None
                    ),
                    "apply_url":        s.link or "",
                    "is_renewal":       True,
                }
                for s, _ in pairs
            ]

            if ScholarshipEmailService.send_renewal_email(user, scholarships_data):
                # Mark each watch as notified for this year only after the
                # email actually succeeded — avoids silently skipping users
                # on retry if the email service was temporarily down.
                watch_ids = [w.id for _, w in pairs]
                WatchedScholarship.objects.filter(id__in=watch_ids).update(
                    notified_for_year=current_year
                )
                emails_sent += 1
            else:
                emails_failed += 1

        logger.info(
            "Renewal notifications complete: %d sent, %d failed",
            emails_sent, emails_failed,
        )
        return {"emails_sent": emails_sent, "emails_failed": emails_failed}

    except Exception as exc:
        logger.error("Renewal notification task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, **RETRY_KWARGS)