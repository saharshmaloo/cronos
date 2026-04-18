import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.scheduler.hourly_prompt import send_hourly_prompt

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    settings = get_settings()
    _scheduler = BackgroundScheduler(timezone=settings.timezone)
    _scheduler.add_job(
        send_hourly_prompt,
        CronTrigger(hour="*", minute=0, timezone=settings.timezone),
        id="hourly_prompt",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started (hourly prompts at :00 %s)", settings.timezone)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
