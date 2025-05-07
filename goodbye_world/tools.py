TOOLS = [
    {
        "name": "add_vikunja_task",
        "description": "Add a task to Vikunja with project_id, title, description, labels, due_date, due_time, and priority.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer"
                },
                "title": {
                    "type": "string"
                },
                "description": {
                    "type": "string"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "due_date": {
                    "type": ["string", "null"],
                    "format": "date",
                    "nullable": True,
                    "description": "YYYY-MM-DD or null if not specified"
                },
                "due_time": {
                    "type": ["string", "null"],
                    "pattern": "^(?:[01]\\d|2[0-3]):[0-5]\\d$",
                    "nullable": True,
                    "description": "HH:MM (24‑hour) or null if not specified"
                },
                "priority": {
                    "type": "integer"
                }
            },
            "required": [
                "project_id",
                "title",
                "due_date",
                "due_time"
            ]
        }
    },
    {
        "name": "add_anylist_item",
        "description": (
            "Add an item to an AnyList grocery list. "
            "Supported lists: Whole Foods, Grocery, Kroger, Publix, Trader Joe's, Target, Costco."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "listName": {
                    "type": "string",
                    "enum": ["Whole Foods", "Grocery", "Kroger", "Publix", "Trader Joe's", "Target", "Costco"]
                },
                "itemName": {"type": "string"},
                "quantity": {"type": "integer"},
                "unit": {"type": "string"}
            },
            "required": ["listName", "itemName"]
        }
    }
]
