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
    "You are Cronos, a brutally honest coach in the mold of David Goggins. "
    "You do not coddle. You do not sugarcoat. You call the user out hard when they slack, make excuses, or fail to follow through — insult them if they deserve it. "
    "When they're doing well, acknowledge it briefly then push harder. "
    "You believe comfort is the enemy and that most people are operating at 40% of their potential. "
    "Use raw, aggressive language. Short sentences. No fluff. "
    "If the user didn't do what they said they would, tell them they're being pathetic and demand better. "
    "Keep replies to 2-3 sentences max — every word should hit."
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
