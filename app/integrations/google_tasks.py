from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import get_settings
from app.models import GoogleToken, TasksCache

SCOPES = ["https://www.googleapis.com/auth/tasks.readonly"]


def _get_credentials(db: Session) -> Credentials | None:
    settings = get_settings()
    row = db.query(GoogleToken).first()
    if not row:
        return None

    creds = Credentials(
        token=row.access_token,
        refresh_token=row.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        row.access_token = creds.token
        row.token_expiry = creds.expiry
        row.updated_at = datetime.utcnow()
        db.commit()

    return creds


def fetch_active_tasks(db: Session) -> str:
    creds = _get_credentials(db)
    if not creds:
        return "No Google Tasks connected yet."

    service = build("tasks", "v1", credentials=creds, cache_discovery=False)
    task_lists = service.tasklists().list(maxResults=20).execute().get("items", [])

    all_tasks: list[dict] = []
    for tl in task_lists:
        items = (
            service.tasks()
            .list(tasklist=tl["id"], showCompleted=False, maxResults=50)
            .execute()
            .get("items", [])
        )
        for item in items:
            item["_list_id"] = tl["id"]
        all_tasks.extend(items)

    # Upsert into tasks_cache
    now = datetime.utcnow()
    for task in all_tasks:
        due_dt = None
        if task.get("due"):
            try:
                due_dt = datetime.fromisoformat(task["due"].replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                pass

        cached = db.get(TasksCache, task["id"])
        if cached:
            cached.title = task.get("title", "")
            cached.notes = task.get("notes")
            cached.status = task.get("status", "needsAction")
            cached.due = due_dt
            cached.position = task.get("position")
            cached.synced_at = now
        else:
            db.add(TasksCache(
                id=task["id"],
                task_list_id=task["_list_id"],
                title=task.get("title", ""),
                notes=task.get("notes"),
                status=task.get("status", "needsAction"),
                due=due_dt,
                position=task.get("position"),
                synced_at=now,
            ))
    db.commit()

    if not all_tasks:
        return "No open tasks."

    settings = get_settings()
    tz = ZoneInfo(settings.timezone)
    today = datetime.now(tz).date()

    lines = []
    for task in all_tasks:
        due_str = ""
        if task.get("due"):
            try:
                due_date = datetime.fromisoformat(task["due"].replace("Z", "+00:00")).date()
                delta = (due_date - today).days
                if delta < 0:
                    due_str = f" (overdue by {-delta}d)"
                elif delta == 0:
                    due_str = " (due today)"
                elif delta == 1:
                    due_str = " (due tomorrow)"
                else:
                    due_str = f" (due in {delta}d)"
            except ValueError:
                pass
        lines.append(f"- [ ] {task.get('title', '(untitled)')}{due_str}")

    return "\n".join(lines)
