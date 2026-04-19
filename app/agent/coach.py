from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import anthropic
from sqlalchemy.orm import Session

from app.config import get_settings, get_app_config, DEFAULT_TONE
from app.models import Message, DailyRating


HOURLY_INJECTION = (
    "[SYSTEM: Hourly check-in. Ask the user what they have been doing since the last check-in. "
    "Be direct — reference their open tasks and name any specific task they should have been "
    "working on. 1-2 sentences max.]"
)


def _get_recent_ratings_text(db: Session, n: int = 7) -> str:
    ratings = (
        db.query(DailyRating)
        .order_by(DailyRating.date.desc())
        .limit(n)
        .all()
    )
    if not ratings:
        return ""
    ratings.reverse()
    lines = [f"{r.date}: {r.rating} — {r.summary}" for r in ratings]
    return "Recent daily ratings (oldest → newest):\n" + "\n".join(lines)


def generate_daily_rating(db: Session, tasks_text: str) -> tuple[str, str]:
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(tz)
    today_midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_utc_start = today_midnight_local.astimezone(timezone.utc).replace(tzinfo=None)

    today_messages = (
        db.query(Message)
        .filter(Message.created_at >= today_utc_start)
        .order_by(Message.created_at.asc())
        .all()
    )

    recent_ratings = (
        db.query(DailyRating)
        .order_by(DailyRating.date.desc())
        .limit(5)
        .all()
    )
    recent_ratings.reverse()

    if recent_ratings:
        lines = [f"{r.date}: {r.rating} — {r.summary}" for r in recent_ratings]
        recent_ratings_text = "Recent daily ratings (oldest → newest):\n" + "\n".join(lines)
    else:
        recent_ratings_text = "No prior ratings. Use an absolute standard for the first rating."

    conversation_text = "\n".join(
        f"[{msg.direction}] {msg.body}" for msg in today_messages
    ) or "No messages recorded today."

    system = (
        "You are an objective performance assessor. "
        "Given the user's activity today and their recent rating trend, decide if today was 'better', 'neutral', or 'worse' than their recent baseline. "
        "Rating is RELATIVE to recent performance — if the last few days were all 'better', today must genuinely exceed that standard to earn 'better' again. "
        "Respond with exactly two lines:\n"
        "Line 1: one word — better, neutral, or worse\n"
        "Line 2: one sentence explaining why, referencing specifics from today."
    )

    user_content = (
        f"{recent_ratings_text}\n\n"
        f"Today's open tasks:\n{tasks_text}\n\n"
        f"Today's conversation log:\n{conversation_text}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )

    lines = response.content[0].text.strip().split("\n", 1)
    rating = lines[0].strip().lower()
    if rating not in ("better", "neutral", "worse"):
        rating = "neutral"
    summary = lines[1].strip() if len(lines) > 1 else ""

    return rating, summary


def generate_coach_response(
    db: Session,
    tasks_text: str,
    user_message: str | None = None,
) -> str:
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    tone = get_app_config("tone_context", db) or DEFAULT_TONE
    ratings_text = _get_recent_ratings_text(db)
    system = (
        f"{tone}\n\n"
        f"Current date/time: {datetime.now(ZoneInfo(settings.timezone)).strftime('%A, %B %d %Y %I:%M %p %Z')}\n\n"
        f"User's open tasks:\n{tasks_text}\n\n"
        + (f"{ratings_text}\n\n" if ratings_text else "")
        + "Keep replies concise — 2-3 sentences max. "
        "When the user tells you what they've been doing, give immediate direct feedback — "
        "name exactly what they did or didn't do, then set the next standard."
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
