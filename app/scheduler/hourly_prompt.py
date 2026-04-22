import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config import get_settings, get_app_config, set_app_config
from app.database import get_session_factory
from app.models import Message
from app.agent.coach import generate_coach_response
from app.integrations.google_tasks import fetch_active_tasks
from app.integrations.telegram_client import send_message

logger = logging.getLogger(__name__)

PAUSE_HOURS = 8
MAX_UNANSWERED = 2


def _unanswered_prompt_count(db: Session) -> int:
    """Count outbound hourly check-ins sent since the user last replied."""
    last_inbound = (
        db.query(Message)
        .filter(Message.direction == "inbound")
        .order_by(Message.created_at.desc())
        .first()
    )
    query = db.query(Message).filter(
        Message.direction == "outbound",
        Message.message_type == "hourly_check_in",
    )
    if last_inbound:
        query = query.filter(Message.created_at > last_inbound.created_at)
    return query.count()


def send_hourly_prompt() -> None:
    SessionLocal = get_session_factory()
    db: Session = SessionLocal()
    try:
        if get_app_config("hourly_prompts_enabled", db) != "true":
            return

        # Check if paused
        just_resumed = False
        paused_until_str = get_app_config("paused_until", db) or ""
        if paused_until_str:
            paused_until = datetime.fromisoformat(paused_until_str)
            if datetime.utcnow() < paused_until:
                logger.info("Hourly prompt skipped — paused until %s UTC", paused_until)
                return
            set_app_config("paused_until", "", db)
            just_resumed = True

        # Check consecutive unanswered prompts (skip after a resume — treat it as a fresh start)
        if not just_resumed:
            unanswered = _unanswered_prompt_count(db)
            if unanswered >= MAX_UNANSWERED:
                resume_at = datetime.utcnow() + timedelta(hours=PAUSE_HOURS)
                set_app_config("paused_until", resume_at.isoformat(), db)
                logger.info("%d unanswered prompts — pausing until %s UTC", unanswered, resume_at)
                return

        settings = get_settings()
        chat_id = settings.telegram_chat_id or get_app_config("telegram_chat_id", db) or ""
        if not chat_id:
            logger.warning("Hourly prompt skipped — no telegram_chat_id configured yet")
            return

        tasks_text = fetch_active_tasks(db)
        prompt_text = generate_coach_response(db, tasks_text=tasks_text, user_message=None)
        msg_id = send_message(prompt_text, chat_id=chat_id)

        db.add(Message(
            direction="outbound",
            role="assistant",
            body=prompt_text,
            message_type="hourly_check_in",
            twilio_sid=str(msg_id) if msg_id else None,
            created_at=datetime.utcnow(),
        ))
        db.commit()
        logger.info("Hourly prompt sent: msg_id=%s", msg_id)

    except Exception:
        logger.exception("Failed to send hourly prompt")
        db.rollback()
    finally:
        db.close()
