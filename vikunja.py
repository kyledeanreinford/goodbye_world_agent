import os
import httpx
from httpx import Timeout

VIKUNJA_URL = os.getenv("VIKUNJA_URL", "http://localhost:3456/api/v1")
VIKUNJA_TOKEN = os.getenv("VIKUNJA_TOKEN")
VIKUNJA_TIMEOUT = Timeout(10.0, connect=5.0)

def create_vikunja_task(task):
    """
    Create a task in Vikunja.
    Expected task keys:
      - project_id (int)
      - title (str)
      - description (optional str)
      - due_date (optional ISO 8601 str)
      - labels (optional list of label IDs)
      - priority (optional int)
    """
    if not VIKUNJA_TOKEN:
        raise ValueError("Missing VIKUNJA_TOKEN environment variable")
    headers = {
        "Authorization": f"Bearer {VIKUNJA_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{VIKUNJA_URL}/projects/{task['project_id']}/tasks"
    payload = {
        "title": task["title"],
        "description": task.get("description", "")
    }
    if "due_date" in task:
        payload["due_date"] = task["due_date"]
    if "labels" in task:
        payload["labels"] = task["labels"]
    if "priority" in task:
        payload["priority"] = task["priority"]
    with httpx.Client(timeout=VIKUNJA_TIMEOUT) as client:
        resp = client.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()