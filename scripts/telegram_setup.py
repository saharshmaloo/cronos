"""
One-time script to register the Telegram webhook URL with your bot.

Usage: uv run python scripts/telegram_setup.py https://cronos.saharshmaloo.com
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.integrations.telegram_client import set_webhook

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/telegram_setup.py https://yourdomain.com")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    webhook_url = f"{base_url}/webhook/telegram"
    result = set_webhook(webhook_url)
    print(result)
