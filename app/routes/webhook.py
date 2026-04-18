import logging
from datetime import datetime
from fastapi import APIRouter, Form, Request, Response, HTTPException
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator

from app.config import get_settings, set_app_config
from app.database import get_session_factory
from app.models import Message
from app.agent.coach import generate_coach_response
from app.integrations.google_tasks import fetch_active_tasks
from app.integrations.twilio_client import send_sms

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


@router.post("/webhook/sms")
async def sms_webhook(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    MessageSid: str = Form(default=""),
):
    settings = get_settings()

    # Validate Twilio signature
    validator = RequestValidator(settings.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    form_data = dict(await request.form())
    url = str(request.url)

    if settings.twilio_auth_token and not validator.validate(url, form_data, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # Guard: only accept messages from the configured user
    # Strip whatsapp: prefix before comparing so both modes work
    from_normalized = From.removeprefix("whatsapp:")
    if settings.user_phone_number and from_normalized != settings.user_phone_number:
        logger.warning("Ignored message from unknown number: %s", From)
        return Response(content="<Response/>", media_type="application/xml")

    SessionLocal = get_session_factory()
    db: Session = SessionLocal()
    try:
        # Any response from the user clears a pause
        set_app_config("paused_until", "", db)

        message_type = _classify_inbound(db)

        inbound = Message(
            direction="inbound",
            role="user",
            body=Body,
            message_type=message_type,
            twilio_sid=MessageSid,
            created_at=datetime.utcnow(),
        )
        db.add(inbound)
        db.commit()

        tasks_text = fetch_active_tasks(db)
        reply_text = generate_coach_response(db, tasks_text=tasks_text, user_message=Body)

        sid = send_sms(reply_text)

        outbound = Message(
            direction="outbound",
            role="assistant",
            body=reply_text,
            message_type="conversation",
            twilio_sid=sid,
            created_at=datetime.utcnow(),
        )
        db.add(outbound)
        db.commit()

    except Exception:
        logger.exception("Error processing inbound SMS")
        db.rollback()
    finally:
        db.close()

    # Always return empty TwiML so Twilio doesn't retry
    return Response(content="<Response/>", media_type="application/xml")
