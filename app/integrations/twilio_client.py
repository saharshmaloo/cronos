from twilio.rest import Client
from app.config import get_settings


def get_twilio_client() -> Client:
    settings = get_settings()
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _wa(number: str) -> str:
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


def send_sms(body: str) -> str:
    settings = get_settings()
    client = get_twilio_client()
    from_ = settings.twilio_phone_number
    to = settings.user_phone_number
    if settings.whatsapp_mode:
        from_ = _wa(from_)
        to = _wa(to)
    msg = client.messages.create(body=body, from_=from_, to=to)
    return msg.sid
