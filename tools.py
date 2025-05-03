TOOLS = [
    {
        "name": "add_vikunja_task",
        "description": "Add a task to Vikunja with specified project_id, title, description, labels, due_date, and priority",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id":     {"type": "integer"},
                "title":          {"type": "string"},
                "description":    {"type": "string"},
                "labels":         {"type": "array", "items": {"type": "string"}},
                "due_date":       {"type": "string", "format": "date-time"},
                "priority":       {"type": "integer"}
            },
            "required": ["project_id", "title"]
        }
    },
    # In future you can append more tools here…
]