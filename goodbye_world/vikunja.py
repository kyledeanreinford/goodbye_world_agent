import logging
import os
from datetime import timezone, datetime

import dateparser
import httpx
from httpx import Timeout

# Configure logger for this module
logger = logging.getLogger(__name__)

VIKUNJA_URL = os.getenv("VIKUNJA_URL", "http://vikunja.thereinfords.com/api/v1")
VIKUNJA_TOKEN = os.getenv("VIKUNJA_TOKEN")
VIKUNJA_TIMEOUT = Timeout(None)


def normalize_due_date(value: str) -> str | None:
    if not value:
        return None

    settings = {
        "RETURN_AS_TIMEZONE_AWARE": True,
        "RELATIVE_BASE": datetime.now(timezone.utc),
        "PREFER_DATES_FROM": "future",
    }

    dt = dateparser.parse(value, settings=settings)
    if not dt:
        return None

    if not dt:
        return None

    if dt.hour == 0 and dt.minute == 0 and " at " not in value.lower():
        dt = dt.replace(hour=23, minute=59, second=0)

    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_vikunja_task(task):
    """
    Create a task in Vikunja.
    Expected task keys:
      - title (str)
      - description (optional str)
      - due_date (optional ISO 8601 str)
      - labels (optional list of label IDs)
      - priority (optional int)
    """
    if not VIKUNJA_TOKEN:
        logger.error("VIKUNJA_TOKEN is not set")
        raise ValueError("Missing VIKUNJA_TOKEN environment variable")

    headers = {
        "Authorization": f"Bearer {VIKUNJA_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{VIKUNJA_URL}/projects/1/tasks"
    payload = {
        "title": task["task_name"],
        "description": task.get("description", "")
    }

    date_raw = task.get("due_date")  # might be ISO or natural
    time_raw = task.get("due_time")  # e.g. "17:00"

    if "due_date" in task:
        normalized = normalize_due_date(task["due_date"])
        if normalized:
            payload["due_date"] = normalized
    if "labels" in task:
        payload["labels"] = task["labels"]
    if "priority" in task:
        payload["priority"] = task["priority"]

    logger.info(
        "Creating Vikunja task - project_id: %s, title: %s",
        0, task["title"]
    )
    logger.debug("POST %s\nHeaders: %s\nPayload: %s", url, headers, payload)

    with httpx.Client(timeout=VIKUNJA_TIMEOUT) as client:
        resp = client.put(url, headers=headers, json=payload)

    logger.info("Vikunja responded with status %s", resp.status_code)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            "Failed to create Vikunja task: %s %s",
            resp.status_code, resp.text
        )
        raise

    logger.debug("Vikunja response body: %s", resp.text)
    return resp.json()
