from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    direction = Column(String(10), nullable=False)   # 'inbound' | 'outbound'
    role = Column(String(10), nullable=False)         # 'user' | 'assistant'
    body = Column(Text, nullable=False)
    message_type = Column(String(30), nullable=False) # 'journal_prompt' | 'journal_entry' | 'conversation' | 'hourly_check_in'
    twilio_sid = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GoogleToken(Base):
    __tablename__ = "google_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=True)
    scope = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TasksCache(Base):
    __tablename__ = "tasks_cache"

    id = Column(String(100), primary_key=True)  # Google Task ID
    task_list_id = Column(String(100), nullable=False)
    title = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False)  # 'needsAction' | 'completed'
    due = Column(DateTime, nullable=True)
    position = Column(String(50), nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow)


class AppConfig(Base):
    __tablename__ = "app_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
