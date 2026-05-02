"""Daily renewal job — runs at 07:00 IST.

For each eligible policy:
1. Check if a reusable completed notice exists (generated at ~30 days before expiry).
2. If reusable, mark source=reused and dispatch notifications.
3. Otherwise create a new RenewalNotice (pending_automation) and dispatch portal task.
"""

import uuid
from datetime import date, timedelta

from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)

TRIGGER_DAYS = {30, 25, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1}


@celery_app.task(name="app.tasks.scheduler.run_daily_renewal_job", bind=True)
def run_daily_renewal_job(self):
    """Entry point for the daily 07:00 IST scheduled job."""
    from app.db.session import SyncSessionLocal
    from app.models.policy import Policy
    from app.models.renewal_notice import NoticeSource, NoticeStatus, RenewalNotice
    from app.models.processing_log import ProcessingLog
    from sqlalchemy import select, and_, or_

    today = date.today()
    logger.info("Daily renewal job started for %s", today)

    stats = {"processed": 0, "reused": 0, "new_automation": 0, "skipped": 0, "errors": 0}

    with SyncSessionLocal() as db:
        policies = db.execute(select(Policy)).scalars().all()

        for policy in policies:
            try:
                days_to_expiry = (policy.policy_expiry_date - today).days

                # --- Eligibility checks ---
                if days_to_expiry not in TRIGGER_DAYS:
                    continue

                if policy.hold_date and policy.hold_date >= today:
                    _log(db, today, policy, "skipped_on_hold", f"hold_date={policy.hold_date}")
                    stats["skipped"] += 1
                    continue

                if policy.renewed_date and policy.renewed_date <= today:
                    _log(db, today, policy, "skipped_already_renewed", f"renewed_date={policy.renewed_date}")
                    stats["skipped"] += 1
                    continue

                if not policy.phone_number and not policy.email:
                    _log(db, today, policy, "skipped_missing_contact", "No phone or email")
                    stats["skipped"] += 1
                    continue

                stats["processed"] += 1

                # --- Check for reusable notice (completed, created within 31 days before expiry) ---
                reuse_cutoff = policy.policy_expiry_date - timedelta(days=31)
                existing = db.execute(
                    select(RenewalNotice).where(
                        and_(
                            RenewalNotice.policy_number == policy.policy_number,
                            RenewalNotice.policy_expiry_date == policy.policy_expiry_date,
                            RenewalNotice.status == NoticeStatus.completed,
                            RenewalNotice.created_at >= reuse_cutoff,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    _log(db, today, policy, "notice_reused", f"notice_id={existing.id}")
                    stats["reused"] += 1
                    # Dispatch notifications for the reused notice
                    from app.tasks.notifications import dispatch_notifications_for_notice
                    dispatch_notifications_for_notice.delay(str(existing.id))
                    continue

                # --- Check if a pending notice already exists (idempotency) ---
                pending = db.execute(
                    select(RenewalNotice).where(
                        and_(
                            RenewalNotice.policy_number == policy.policy_number,
                            RenewalNotice.policy_expiry_date == policy.policy_expiry_date,
                            RenewalNotice.status.in_([
                                NoticeStatus.pending_automation,
                                NoticeStatus.pending_manual_upload,
                            ]),
                        )
                    )
                ).scalar_one_or_none()

                if pending:
                    _log(db, today, policy, "notice_already_pending", f"notice_id={pending.id}")
                    continue

                # --- Create new notice and dispatch portal task ---
                notice = RenewalNotice(
                    policy_id=policy.id,
                    insurance_provider_id=policy.insurance_provider_id,
                    policy_number=policy.policy_number,
                    policy_expiry_date=policy.policy_expiry_date,
                    customer_name=policy.customer_name,
                    date_of_birth=policy.date_of_birth,
                    phone_number=policy.phone_number,
                    email=policy.email,
                    type_of_policy=policy.type_of_policy,
                    hold_date=policy.hold_date,
                    renewed_date=policy.renewed_date,
                    status=NoticeStatus.pending_automation,
                )
                db.add(notice)
                db.flush()

                _log(db, today, policy, "notice_created", f"notice_id={notice.id}")
                stats["new_automation"] += 1

                from app.tasks.portal import generate_renewal_notice
                generate_renewal_notice.delay(str(notice.id))

            except Exception as exc:
                logger.exception("Error processing policy %s: %s", policy.policy_number, exc)
                _log(db, today, policy, "error", str(exc))
                stats["errors"] += 1

        db.commit()

    logger.info("Daily renewal job complete: %s", stats)

    # Send daily summary to agents
    from app.tasks.alerts import send_daily_summary
    send_daily_summary.delay(today.isoformat(), stats)

    return stats


def _log(db, run_date, policy, action: str, detail: str = None):
    from app.models.processing_log import ProcessingLog
    log = ProcessingLog(
        run_date=run_date,
        policy_id=policy.id,
        policy_number=policy.policy_number,
        action=action,
        detail=detail,
    )
    db.add(log)
