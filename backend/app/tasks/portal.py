"""Portal automation task.

Attempts headless Playwright login to the insurer portal to download the renewal
notice PDF. Retries up to 3 times with exponential backoff. On exhaustion, sets
the notice to pending_manual_upload and fires an agent failure alert.
"""

import json
import tempfile
import uuid
from pathlib import Path

from celery.utils.log import get_task_logger
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)

# Retry delays: 60s, 300s, 900s
RETRY_WAIT = wait_exponential(multiplier=60, min=60, max=900)
RETRY_STOP = stop_after_attempt(3)


@celery_app.task(name="app.tasks.portal.generate_renewal_notice", bind=True)
def generate_renewal_notice(self, notice_id: str):
    """Download renewal document from insurer portal for a given RenewalNotice."""
    from app.db.session import SyncSessionLocal
    from app.models.renewal_notice import NoticeSource, NoticeStatus, RenewalNotice
    from app.models.insurance_provider import InsuranceProvider
    from app.core.security import decrypt_credentials
    from sqlalchemy import select

    with SyncSessionLocal() as db:
        notice = db.execute(select(RenewalNotice).where(RenewalNotice.id == uuid.UUID(notice_id))).scalar_one_or_none()
        if not notice:
            logger.error("Notice %s not found", notice_id)
            return

        if notice.status == NoticeStatus.completed:
            logger.info("Notice %s already completed, skipping", notice_id)
            return

        provider = db.execute(
            select(InsuranceProvider).where(InsuranceProvider.id == notice.insurance_provider_id)
        ).scalar_one_or_none()

        if not provider:
            logger.error("Provider not found for notice %s", notice_id)
            _mark_failed(db, notice, "Provider record not found")
            db.commit()
            return

        credentials = json.loads(decrypt_credentials(provider.login_credentials_encrypted))
        additional_auth = (
            json.loads(decrypt_credentials(provider.additional_auth_encrypted))
            if provider.additional_auth_encrypted
            else {}
        )

        try:
            pdf_bytes, filename = _attempt_portal_download(
                portal_url=provider.portal_url,
                credentials=credentials,
                additional_auth=additional_auth,
                policy_number=notice.policy_number,
            )
            notice.renewal_document = pdf_bytes
            notice.document_filename = filename
            notice.status = NoticeStatus.completed
            notice.source = NoticeSource.automated
            db.commit()
            logger.info("Portal automation succeeded for notice %s", notice_id)

            # Dispatch notifications
            from app.tasks.notifications import dispatch_notifications_for_notice
            dispatch_notifications_for_notice.delay(notice_id)

        except Exception as exc:
            logger.warning("Portal automation failed for notice %s: %s", notice_id, exc)
            notice.status = NoticeStatus.pending_manual_upload
            db.commit()

            # Alert agents
            from app.tasks.alerts import send_failure_alert
            send_failure_alert.delay(
                notice_id=notice_id,
                policy_number=notice.policy_number,
                provider_name=provider.provider_name,
                reason=str(exc),
            )


@retry(stop=RETRY_STOP, wait=RETRY_WAIT, reraise=True)
def _attempt_portal_download(
    portal_url: str,
    credentials: dict,
    additional_auth: dict,
    policy_number: str,
) -> tuple[bytes, str]:
    """
    Attempt to log in to the insurer portal and download the renewal notice PDF.

    This function uses Playwright in headless mode. Each insurer portal has
    different login flows; the credentials dict must contain at minimum:
      - username / password
    Additional auth may contain OTP seeds or security question answers.

    Because portals vary widely, this implementation provides the scaffolding.
    Per-provider automation scripts should be placed in app/services/portal_adapters/
    and selected by provider_name. The base implementation below demonstrates
    the pattern for a generic username/password portal.

    Raises an exception on any failure so tenacity can retry.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    username = credentials.get("username", "")
    password = credentials.get("password", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            page.goto(portal_url, timeout=30_000)

            # Generic login — override per provider adapter
            page.fill('input[name="username"], input[type="email"], #username', username)
            page.fill('input[name="password"], input[type="password"], #password', password)
            page.click('button[type="submit"], input[type="submit"], .login-btn')
            page.wait_for_load_state("networkidle", timeout=15_000)

            # Check for CAPTCHA / OTP indicators
            captcha_indicators = ["captcha", "recaptcha", "otp", "one-time", "verification code"]
            page_text = page.content().lower()
            if any(indicator in page_text for indicator in captcha_indicators):
                raise RuntimeError(
                    "CAPTCHA or OTP detected on portal — manual intervention required"
                )

            # Search for policy
            page.fill('input[name="policyNumber"], input[placeholder*="policy"], #policyNo', policy_number)
            page.click('button:has-text("Search"), button:has-text("Find"), input[value="Search"]')
            page.wait_for_load_state("networkidle", timeout=15_000)

            # Download renewal notice
            with page.expect_download(timeout=30_000) as download_info:
                page.click(
                    'a:has-text("Renewal"), button:has-text("Renewal Notice"), '
                    'a:has-text("Download"), .renewal-notice-download'
                )
            download = download_info.value

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                download.save_as(tmp.name)
                pdf_bytes = Path(tmp.name).read_bytes()

            filename = download.suggested_filename or f"renewal_{policy_number}.pdf"
            return pdf_bytes, filename

        except PlaywrightTimeout as exc:
            raise RuntimeError(f"Portal timeout: {exc}") from exc
        finally:
            context.close()
            browser.close()


def _mark_failed(db, notice, reason: str):
    from app.models.renewal_notice import NoticeStatus
    notice.status = NoticeStatus.failed
    logger.error("Marking notice %s as failed: %s", notice.id, reason)
