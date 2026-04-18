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
    "You are a warm, direct personal coach named Cronos. "
    "You hold the user accountable without being harsh. "
    "You ask focused questions, celebrate small wins, and surface patterns. "
    "You never lecture. Keep replies concise — 2-3 sentences max."
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
