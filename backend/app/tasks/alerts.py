"""Agent alert emails — failure alerts and daily summary."""

import resend
from celery.utils.log import get_task_logger

from app.core.config import get_settings
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)
settings = get_settings()


@celery_app.task(name="app.tasks.alerts.send_failure_alert", bind=True)
def send_failure_alert(self, notice_id: str, policy_number: str, provider_name: str, reason: str):
    """Email agents when portal automation exhausts all retries."""
    recipients = settings.agent_alert_email_list
    if not recipients:
        logger.warning("No agent alert recipients configured")
        return

    subject = f"[Action Required] Renewal notice failed — {policy_number}"
    body = (
        f"Portal automation failed for the following policy after 3 attempts.\n\n"
        f"Policy Number : {policy_number}\n"
        f"Provider      : {provider_name}\n"
        f"Reason        : {reason}\n"
        f"Notice ID     : {notice_id}\n\n"
        f"Please log in to the dashboard, locate this notice under "
        f"'Pending Manual Upload', download the document from the insurer portal, "
        f"and upload it manually.\n\n"
        f"— Veekay Finserve Renewal System"
    )

    _send_alert_email(recipients=recipients, subject=subject, body=body)
    logger.info("Failure alert sent for notice %s", notice_id)


@celery_app.task(name="app.tasks.alerts.send_daily_summary", bind=True)
def send_daily_summary(self, run_date: str, stats: dict):
    """Email agents a summary of the day's renewal job results."""
    recipients = settings.agent_alert_email_list
    if not recipients:
        logger.warning("No agent alert recipients configured")
        return

    pending_manual = _count_pending_manual()

    subject = f"[Daily Summary] Renewal job — {run_date}"
    body = (
        f"Daily renewal job completed for {run_date}.\n\n"
        f"Policies processed      : {stats.get('processed', 0)}\n"
        f"Notices reused          : {stats.get('reused', 0)}\n"
        f"New automation tasks    : {stats.get('new_automation', 0)}\n"
        f"Skipped                 : {stats.get('skipped', 0)}\n"
        f"Errors                  : {stats.get('errors', 0)}\n\n"
        f"Pending manual upload   : {pending_manual}\n\n"
        f"{'⚠️  Action required: ' + str(pending_manual) + ' notice(s) need manual document upload.' if pending_manual else 'No manual action required today.'}\n\n"
        f"— Veekay Finserve Renewal System"
    )

    _send_alert_email(recipients=recipients, subject=subject, body=body)
    logger.info("Daily summary sent for %s", run_date)


def _count_pending_manual() -> int:
    try:
        from app.db.session import SyncSessionLocal
        from app.models.renewal_notice import RenewalNotice, NoticeStatus
        from sqlalchemy import select, func

        with SyncSessionLocal() as db:
            result = db.execute(
                select(func.count(RenewalNotice.id)).where(
                    RenewalNotice.status == NoticeStatus.pending_manual_upload
                )
            )
            return result.scalar_one()
    except Exception as exc:
        logger.error("Could not count pending manual notices: %s", exc)
        return 0


def _send_alert_email(recipients: list[str], subject: str, body: str):
    resend.api_key = settings.RESEND_API_KEY
    params = resend.Emails.SendParams(
        from_=f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
        to=recipients,
        subject=subject,
        text=body,
    )
    resend.Emails.send(params)
