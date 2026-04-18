"""
Update the coach tone context in the database.

Usage: uv run python scripts/set_tone.py
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DEFAULT_TONE, set_app_config
from app.models import Base

def main():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/coach.db")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    print("Current tone will be replaced with:\n")
    print(DEFAULT_TONE)
    print()
    confirm = input("Apply? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    set_app_config("tone_context", DEFAULT_TONE, db)
    print("Tone updated.")

if __name__ == "__main__":
    main()
