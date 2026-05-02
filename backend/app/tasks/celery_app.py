from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "veekay_renewals",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.scheduler",
        "app.tasks.portal",
        "app.tasks.notifications",
        "app.tasks.alerts",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=settings.SCHEDULER_TIMEZONE,
    enable_utc=False,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
)

celery_app.conf.beat_schedule = {
    "daily-renewal-job": {
        "task": "app.tasks.scheduler.run_daily_renewal_job",
        "schedule": crontab(hour=7, minute=0),
    },
}
