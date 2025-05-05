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
                "listName": {
                    "type": "string",
                    "enum": ["Whole Foods", "Grocery", "Kroger", "Publix", "Trader Joe's", "Target", "Costco"]
                },
                "itemName": {"type": "string"},
                "quantity":  {"type": "integer"},
                "unit":      {"type": "string"}
            },
            "required": ["listName", "itemName"]
        }
    }
]