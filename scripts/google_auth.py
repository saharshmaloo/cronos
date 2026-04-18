"""
One-time script to authorize Google Tasks access and store tokens in the DB.

Usage:
  1. Download OAuth2 Desktop App credentials from Google Cloud Console
     and save as credentials.json in the project root.
  2. Run: uv run python scripts/google_auth.py
  3. Complete the browser consent flow.
  4. Tokens are saved to the database automatically.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from google_auth_oauthlib.flow import InstalledAppFlow
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, GoogleToken

SCOPES = ["https://www.googleapis.com/auth/tasks.readonly"]


def main():
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    print("Opening browser for Google authorization...")
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0)

    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/coach.db")
    os.makedirs("data", exist_ok=True)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    existing = db.query(GoogleToken).first()
    if existing:
        existing.access_token = creds.token
        existing.refresh_token = creds.refresh_token
        existing.token_expiry = creds.expiry
        existing.scope = " ".join(creds.scopes or [])
        existing.updated_at = datetime.utcnow()
    else:
        db.add(GoogleToken(
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            token_expiry=creds.expiry,
            scope=" ".join(creds.scopes or []),
            updated_at=datetime.utcnow(),
        ))

    db.commit()
    db.close()
    print("Google OAuth tokens saved to database.")


if __name__ == "__main__":
    main()
