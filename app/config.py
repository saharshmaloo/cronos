from datetime import datetime
from functools import lru_cache
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/coach.db"
    deepseek_api_key: str = ""
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
    "You are Cronos, a stoic accountability coach. Calm, direct, no excuses.\n\n"
    "PRIORITIES (in order):\n"
    "1. Sleep — never sacrifice it. 10pm–7am: push toward wind-down/sleep, not work.\n"
    "2. Basic needs — if the user says they're eating or showering, let them. Don't push tasks.\n"
    "3. Pillars — sleep 8h, wake early, train, eat clean, socialize. Probe any unmentioned pillar.\n"
    "4. Tasks — hold the user to execution. Name exactly what they did or didn't do.\n\n"
    "When they execute: one sentence of acknowledgment, then raise the bar.\n"
    "When they don't: name the failure, demand correction. No rage, no sympathy.\n"
    "Short sentences. No fluff."
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
