import httpx
from app.config import get_settings

BASE = "https://api.telegram.org"


def send_message(text: str, chat_id: str | None = None) -> int | None:
    settings = get_settings()
    cid = chat_id or settings.telegram_chat_id
    if not cid:
        raise ValueError("No telegram_chat_id configured")
    resp = httpx.post(
        f"{BASE}/bot{settings.telegram_bot_token}/sendMessage",
        json={"chat_id": cid, "text": text},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("result", {}).get("message_id")


def set_webhook(url: str) -> dict:
    settings = get_settings()
    payload: dict = {"url": url}
    if settings.telegram_webhook_secret:
        payload["secret_token"] = settings.telegram_webhook_secret
    resp = httpx.post(
        f"{BASE}/bot{settings.telegram_bot_token}/setWebhook",
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
