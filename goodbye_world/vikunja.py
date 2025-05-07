import os
import logging
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
    parsed = dateparser.parse(value)
    if not parsed:
        return None
    return parsed.strftime("%Y-%m-%d")


def create_vikunja_task(task):
    """
    Create a task in Vikunja.
    Expected task keys:
      - task_name (str)
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
        0, task["task_name"]
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