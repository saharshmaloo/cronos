from datetime import datetime
import anthropic
from sqlalchemy.orm import Session

from app.config import get_settings, get_app_config, DEFAULT_TONE
from app.models import Message


HOURLY_INJECTION = (
    "[SYSTEM: This is an automated hourly check-in. Generate a brief, warm journal prompt "
    "for the user. Consider their open tasks. Keep it to 1-2 sentences max.]"
)


def generate_coach_response(
    db: Session,
    tasks_text: str,
    user_message: str | None = None,
) -> str:
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    tone = get_app_config("tone_context", db) or DEFAULT_TONE
    system = (
        f"{tone}\n\n"
        f"Current date/time: {datetime.now().strftime('%A, %B %d %Y %I:%M %p %Z')}\n\n"
        f"User's open tasks:\n{tasks_text}\n\n"
        "Keep replies concise — 2-3 sentences max."
    )

    limit = settings.context_window_messages
    history = (
        db.query(Message)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    history.reverse()

    messages = [{"role": msg.role, "content": msg.body} for msg in history]

    if user_message:
        messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": HOURLY_INJECTION})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=system,
        messages=messages,
    )

    return response.content[0].text
