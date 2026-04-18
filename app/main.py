import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import seed_app_config
from app.database import get_session_factory
from app.routes.health import router as health_router
from app.routes.webhook import router as webhook_router
from app.scheduler.jobs import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        seed_app_config(db)
    finally:
        db.close()

    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Cronos", lifespan=lifespan)
app.include_router(health_router)
app.include_router(webhook_router)
