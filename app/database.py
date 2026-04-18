import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL", "sqlite:///./data/coach.db")
        _engine = create_engine(url, connect_args={"check_same_thread": False})
    return _engine


def get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Session:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
