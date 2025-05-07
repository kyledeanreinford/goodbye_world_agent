import os
import logging
import httpx
import dateparser
from datetime import timezone, datetime
from httpx import Timeout

logger = logging.getLogger(__name__)

VIKUNJA_URL     = os.getenv("VIKUNJA_URL", "http://vikunja.thereinfords.com/api/v1")
VIKUNJA_TOKEN   = os.getenv("VIKUNJA_TOKEN")
VIKUNJA_TIMEOUT = Timeout(30.0, connect=10.0)

def normalize_due_date(value: str) -> str | None:
    if not value:
        return None

    settings = {
        "RETURN_AS_TIMEZONE_AWARE": True,
        "TIMEZONE":                 "America/Chicago",
        "TO_TIMEZONE":              "UTC",
        "PREFER_DATES_FROM":        "future"
    }
    dt = dateparser.parse(value, settings=settings)
    if not dt:
        return None

    if dt.hour == 0 and dt.minute == 0 and " at " not in value.lower():
        dt = dt.replace(hour=23, minute=59, second=0)

    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_vikunja_task(task):
    if not VIKUNJA_TOKEN:
        raise ValueError("Missing VIKUNJA_TOKEN")

    headers = {
        "Authorization": f"Bearer {VIKUNJA_TOKEN}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }

    # pick title key
    title = task.get("title") or task.get("task_name")
    if not title:
        logger.error("Missing title/task_name in args: %s", task)
        raise KeyError("title")

    # build payload
    payload = {
        "title":       title,
        "description": task.get("description", "")
    }

    # handle date+time
    date_raw = task.get("due_date")
    time_raw = task.get("due_time")
    if date_raw:
        if not time_raw:
            time_raw = "23:59"
        combined = f"{date_raw} {time_raw}"
        logger.debug("Parsing due at %r", combined)
        normalized = normalize_due_date(combined)
        if normalized:
            payload["due_date"] = normalized

    if "priority" in task:
        payload["priority"] = task["priority"]

    # create the task
    url = f"{VIKUNJA_URL}/projects/1/tasks"
    logger.info("Creating task: %s", payload)
    with httpx.Client(timeout=VIKUNJA_TIMEOUT) as client:
        resp = client.put(url, headers=headers, json=payload)
        resp.raise_for_status()
        created = resp.json()

    logger.info("Task created: %s", created["id"])
    return created