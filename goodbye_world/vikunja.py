import os
import logging
from datetime import time, timezone, datetime

import httpx
from httpx import Timeout
import dateparser

# Configure logger for this module
logger = logging.getLogger(__name__)

VIKUNJA_URL = os.getenv("VIKUNJA_URL", "http://vikunja.thereinfords.com/api/v1")
VIKUNJA_TOKEN = os.getenv("VIKUNJA_TOKEN")
VIKUNJA_TIMEOUT = Timeout(None)


def normalize_due_date(value):
    if not value:
        return None

    now = datetime.now(timezone.utc)
    parsed = dateparser.parse(
        value,
        settings={
            "RETURN_AS_TIMEZONE_AWARE": True,
            "RELATIVE_BASE": now,
            "PREFER_DATES_FROM": "future"
        }
    )

    if not parsed:
        return None

    # If user said "tomorrow" with no time, assume end-of-day
    if parsed.time() == time(0, 0):
        parsed = parsed.replace(hour=23, minute=59, second=59)

    parsed_utc = parsed.astimezone(timezone.utc)
    return parsed_utc.isoformat().replace("+00:00", "Z")


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
        "title": task["title"],
        "description": task.get("description", "")
    }

    if "due_date" in task:
        normalized_date = normalize_due_date(task["due_date"])
        if normalized_date:
            payload["due_date"] = normalized_date

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
