TOOLS = [
    {
        "name": "add_vikunja_task",
        "description": "Add a task to Vikunja with project_id, title, description, labels, due_date, and priority.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id":  {"type": "integer"},
                "title":       {"type": "string"},
                "description": {"type": "string"},
                "labels":      {"type": "array",  "items": {"type": "string"}},
                "due_date":    {"type": "string", "format": "date-time"},
                "priority":    {"type": "integer"}
            },
            "required": ["project_id", "title"]
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
                "list_name": {
                    "type": "string",
                    "enum": ["Whole Foods", "Grocery", "Kroger", "Publix", "Trader Joe's", "Target", "Costco"]
                },
                "item_name": {"type": "string"},
                "quantity":  {"type": "integer"},
                "unit":      {"type": "string"}
            },
            "required": ["list_name", "item_name"]
        }
    }
]