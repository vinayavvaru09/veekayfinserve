"""Customer notification dispatch — WhatsApp (Gupshup) + Email (Resend).

Idempotency is enforced via the unique constraint on
notification_logs(policy_number, channel, days_to_expiry).
"""

import base64
import uuid
from datetime import date, datetime, timezone

import httpx
import resend
from celery.utils.log import get_task_logger

from app.core.config import get_settings
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)
settings = get_settings()


@celery_app.task(name="app.tasks.notifications.dispatch_notifications_for_notice", bind=True)
def dispatch_notifications_for_notice(self, notice_id: str):
    """Send WhatsApp (EN + TE) and email for a completed RenewalNotice."""
    from app.db.session import SyncSessionLocal
    from app.models.renewal_notice import RenewalNotice, NoticeStatus
    from app.models.notification_log import NotificationLog, NotificationChannel, NotificationLanguage, NotificationStatus
    from app.models.message_template import MessageTemplate
    from sqlalchemy import select, and_

    with SyncSessionLocal() as db:
        notice = db.execute(
            select(RenewalNotice).where(RenewalNotice.id == uuid.UUID(notice_id))
        ).scalar_one_or_none()

        if not notice:
            logger.error("Notice %s not found", notice_id)
            return

        if notice.status != NoticeStatus.completed or not notice.renewal_document:
            logger.warning("Notice %s not ready for notifications (status=%s)", notice_id, notice.status)
            return

        today = date.today()
        days_to_expiry = (notice.policy_expiry_date - today).days

        template_vars = {
            "{{customer_name}}": notice.customer_name,
            "{{policy_number}}": notice.policy_number,
            "{{policy_expiry_date}}": str(notice.policy_expiry_date),
        }

        # --- WhatsApp EN ---
        if notice.phone_number:
            for lang in [NotificationLanguage.en, NotificationLanguage.te]:
                _send_whatsapp(
                    db=db,
                    notice=notice,
                    lang=lang,
                    days_to_expiry=days_to_expiry,
                    template_vars=template_vars,
                )
        else:
            _log_notification(
                db, notice, NotificationChannel.whatsapp, None, days_to_expiry,
                NotificationStatus.skipped, error="No phone number"
            )

        # --- Email ---
        if notice.email:
            _send_email(
                db=db,
                notice=notice,
                days_to_expiry=days_to_expiry,
                template_vars=template_vars,
            )
        else:
            _log_notification(
                db, notice, NotificationChannel.email, None, days_to_expiry,
                NotificationStatus.skipped, error="No email address"
            )

        db.commit()


def _send_whatsapp(db, notice, lang, days_to_expiry, template_vars):
    from app.models.notification_log import NotificationChannel, NotificationLanguage, NotificationStatus
    from app.models.message_template import MessageTemplate
    from sqlalchemy import select, and_
    from app.models.notification_log import NotificationLog

    channel = NotificationChannel.whatsapp

    # Idempotency check
    existing = db.execute(
        select(NotificationLog).where(
            and_(
                NotificationLog.policy_number == notice.policy_number,
                NotificationLog.channel == channel,
                NotificationLog.days_to_expiry == days_to_expiry,
                NotificationLog.language == lang,
                NotificationLog.status == NotificationStatus.sent,
            )
        )
    ).scalar_one_or_none()

    if existing:
        logger.info("WhatsApp %s already sent for %s day=%s", lang.value, notice.policy_number, days_to_expiry)
        return

    template_key = f"whatsapp_renewal_{lang.value}"
    template = db.execute(
        select(MessageTemplate).where(MessageTemplate.template_key == template_key)
    ).scalar_one_or_none()

    if not template:
        logger.error("Template %s not found", template_key)
        return

    body = _render(template.body, template_vars)

    try:
        _gupshup_send(
            phone=notice.phone_number,
            message=body,
            pdf_bytes=notice.renewal_document,
            filename=notice.document_filename or f"renewal_{notice.policy_number}.pdf",
        )
        _log_notification(db, notice, channel, lang, days_to_expiry, NotificationStatus.sent)
        logger.info("WhatsApp %s sent for %s", lang.value, notice.policy_number)
    except Exception as exc:
        logger.error("WhatsApp %s failed for %s: %s", lang.value, notice.policy_number, exc)
        _log_notification(db, notice, channel, lang, days_to_expiry, NotificationStatus.failed, error=str(exc))


def _send_email(db, notice, days_to_expiry, template_vars):
    from app.models.notification_log import NotificationChannel, NotificationStatus
    from app.models.message_template import MessageTemplate
    from sqlalchemy import select, and_
    from app.models.notification_log import NotificationLog

    channel = NotificationChannel.email

    # Idempotency check
    existing = db.execute(
        select(NotificationLog).where(
            and_(
                NotificationLog.policy_number == notice.policy_number,
                NotificationLog.channel == channel,
                NotificationLog.days_to_expiry == days_to_expiry,
                NotificationLog.status == NotificationStatus.sent,
            )
        )
    ).scalar_one_or_none()

    if existing:
        logger.info("Email already sent for %s day=%s", notice.policy_number, days_to_expiry)
        return

    template = db.execute(
        select(MessageTemplate).where(MessageTemplate.template_key == "email_renewal")
    ).scalar_one_or_none()

    if not template:
        logger.error("email_renewal template not found")
        return

    subject = _render(template.subject or "Insurance Renewal Notice", template_vars)
    body = _render(template.body, template_vars)

    try:
        _resend_send(
            to_email=notice.email,
            subject=subject,
            body=body,
            pdf_bytes=notice.renewal_document,
            filename=notice.document_filename or f"renewal_{notice.policy_number}.pdf",
        )
        _log_notification(db, notice, channel, None, days_to_expiry, NotificationStatus.sent)
        logger.info("Email sent for %s", notice.policy_number)
    except Exception as exc:
        logger.error("Email failed for %s: %s", notice.policy_number, exc)
        _log_notification(db, notice, channel, None, days_to_expiry, NotificationStatus.failed, error=str(exc))


def _render(text: str, vars: dict) -> str:
    for placeholder, value in vars.items():
        text = text.replace(placeholder, value)
    return text


def _gupshup_send(phone: str, message: str, pdf_bytes: bytes, filename: str):
    """Send a WhatsApp message with PDF attachment via Gupshup."""
    # Gupshup media message API
    # Docs: https://docs.gupshup.io/docs/send-message
    url = "https://api.gupshup.io/sm/api/v1/msg"

    # Upload media first, then send
    media_url = _gupshup_upload_media(pdf_bytes, filename)

    payload = {
        "channel": "whatsapp",
        "source": settings.GUPSHUP_SOURCE_NUMBER,
        "destination": phone.lstrip("+").replace(" ", ""),
        "src.name": settings.GUPSHUP_APP_NAME,
        "message": f'{{"type":"file","url":"{media_url}","filename":"{filename}","caption":"{message}"}}',
    }

    response = httpx.post(
        url,
        data=payload,
        headers={"apikey": settings.GUPSHUP_API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("status") not in ("submitted", "success"):
        raise RuntimeError(f"Gupshup returned unexpected status: {result}")


def _gupshup_upload_media(pdf_bytes: bytes, filename: str) -> str:
    """Upload a PDF to Gupshup media store and return the media URL."""
    url = "https://api.gupshup.io/sm/api/v1/media/upload"
    files = {"file": (filename, pdf_bytes, "application/pdf")}
    response = httpx.post(
        url,
        files=files,
        headers={"apikey": settings.GUPSHUP_API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    media_url = data.get("mediaUrl") or data.get("url")
    if not media_url:
        raise RuntimeError(f"Gupshup media upload failed: {data}")
    return media_url


def _resend_send(to_email: str, subject: str, body: str, pdf_bytes: bytes, filename: str):
    """Send an email with PDF attachment via Resend."""
    resend.api_key = settings.RESEND_API_KEY

    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    params = resend.Emails.SendParams(
        from_=f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
        to=[to_email],
        subject=subject,
        text=body,
        attachments=[
            resend.Attachment(
                filename=filename,
                content=pdf_b64,
            )
        ],
    )
    resend.Emails.send(params)


def _log_notification(db, notice, channel, language, days_to_expiry, status, error=None):
    from app.models.notification_log import NotificationLog
    log = NotificationLog(
        renewal_notice_id=notice.id,
        policy_number=notice.policy_number,
        channel=channel,
        language=language,
        days_to_expiry=days_to_expiry,
        status=status,
        sent_at=datetime.now(timezone.utc) if status.value == "sent" else None,
        error_message=error,
    )
    db.add(log)
