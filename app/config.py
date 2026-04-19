from datetime import datetime
from functools import lru_cache
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/coach.db"
    anthropic_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""          # optional — auto-detected from first message
    telegram_webhook_secret: str = ""   # optional but recommended
    timezone: str = "America/New_York"
    context_window_messages: int = 20
    port: int = 8000

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


DEFAULT_TONE = (
    "You are Cronos, a high-standards accountability coach. "
    "You operate with the discipline of a Navy SEAL and the detachment of a stoic — calm, direct, and completely unimpressed by excuses. "
    "You hold the user to one standard: did they execute or not? "
    "When they didn't, name exactly what they failed to do and what it cost them, then demand they correct it immediately. No sympathy, no insults — just cold clarity. "
    "When they execute well, acknowledge it in one sentence, then raise the bar. "
    "You believe most people are capable of far more than they're currently doing, and your job is to close that gap through relentless standards — not rage. "
    "Short sentences. No fluff. Every word earns its place."
)

DEFAULT_CONFIG = {
    "tone_context": DEFAULT_TONE,
    "hourly_prompts_enabled": "true",
    "paused_until": "",
    "telegram_chat_id": "",
}


def seed_app_config(db: Session) -> None:
    from app.models import AppConfig
    for key, value in DEFAULT_CONFIG.items():
        existing = db.get(AppConfig, key)
        if existing is None:
            db.add(AppConfig(key=key, value=value, updated_at=datetime.utcnow()))
    db.commit()


def get_app_config(key: str, db: Session) -> str | None:
    from app.models import AppConfig
    row = db.get(AppConfig, key)
    return row.value if row else None


def set_app_config(key: str, value: str, db: Session) -> None:
    from app.models import AppConfig
    row = db.get(AppConfig, key)
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        db.add(AppConfig(key=key, value=value, updated_at=datetime.utcnow()))
    db.commit()
