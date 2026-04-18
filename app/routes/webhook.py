import logging
from datetime import datetime
from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings, get_app_config, set_app_config
from app.database import get_session_factory
from app.models import Message
from app.agent.coach import generate_coach_response
from app.integrations.google_tasks import fetch_active_tasks
from app.integrations.telegram_client import send_message

logger = logging.getLogger(__name__)
router = APIRouter()


def _classify_inbound(db: Session) -> str:
    last_outbound = (
        db.query(Message)
        .filter(Message.direction == "outbound")
        .order_by(Message.created_at.desc())
        .first()
    )
    if last_outbound and last_outbound.message_type in ("journal_prompt", "hourly_check_in"):
        return "journal_entry"
    return "conversation"


def _resolve_chat_id(incoming_id: str, db: Session) -> str | None:
    settings = get_settings()
    configured = settings.telegram_chat_id or get_app_config("telegram_chat_id", db) or ""

    if not configured:
        # Auto-detect: first person to message the bot becomes the owner
        set_app_config("telegram_chat_id", incoming_id, db)
        logger.info("Auto-configured telegram_chat_id: %s", incoming_id)
        return incoming_id

    if incoming_id != configured:
        logger.warning("Ignored message from unknown chat: %s", incoming_id)
        return None

    return configured


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    settings = get_settings()

    # Validate secret token if configured
    if settings.telegram_webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != settings.telegram_webhook_secret:
            return Response(status_code=403)

    update = await request.json()

    message = update.get("message") or update.get("edited_message")
    if not message:
        return Response(status_code=200)

    text = message.get("text", "").strip()
    chat_id = str(message["chat"]["id"])

    if not text:
        return Response(status_code=200)

    SessionLocal = get_session_factory()
    db: Session = SessionLocal()
    try:
        resolved = _resolve_chat_id(chat_id, db)
        if resolved is None:
            return Response(status_code=200)

        # Any response clears a pause
        set_app_config("paused_until", "", db)

        message_type = _classify_inbound(db)

        db.add(Message(
            direction="inbound",
            role="user",
            body=text,
            message_type=message_type,
            twilio_sid=str(message.get("message_id")),
            created_at=datetime.utcnow(),
        ))
        db.commit()

        tasks_text = fetch_active_tasks(db)
        reply_text = generate_coach_response(db, tasks_text=tasks_text, user_message=text)

        msg_id = send_message(reply_text, chat_id=resolved)

        db.add(Message(
            direction="outbound",
            role="assistant",
            body=reply_text,
            message_type="conversation",
            twilio_sid=str(msg_id) if msg_id else None,
            created_at=datetime.utcnow(),
        ))
        db.commit()

    except Exception:
        logger.exception("Error processing Telegram message")
        db.rollback()
    finally:
        db.close()

    return Response(status_code=200)
