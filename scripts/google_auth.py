"""
One-time script to authorize Google Tasks access and store tokens in the DB.
Works on headless servers (EC2) — no browser required on the server.

Usage: uv run python scripts/google_auth.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from google_auth_oauthlib.flow import InstalledAppFlow
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, GoogleToken

SCOPES = ["https://www.googleapis.com/auth/tasks.readonly"]
REDIRECT_URI = "http://localhost:1"  # won't load, but Google echoes the code in the URL


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
            "redirect_uris": [REDIRECT_URI, "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI

    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")

    print("\n1. Open this URL in your browser:\n")
    print(f"   {auth_url}\n")
    print("2. Approve access. Your browser will show a 'connection refused' page — that's expected.")
    print("3. Copy the full URL from your browser's address bar and paste it below.\n")

    redirect_response = input("Paste the redirect URL: ").strip()

    flow.fetch_token(authorization_response=redirect_response)
    creds = flow.credentials

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
    print("\nGoogle OAuth tokens saved to database.")


if __name__ == "__main__":
    main()
