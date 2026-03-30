from typing import Any


TASKS: dict[str, dict[str, Any]] = {
    "easy": {
        "name": "easy",
        "difficulty": "easy",
        "description": "Reduce VRAM below 50% without OOM using evict/retain only.",
        "action_schema": {
            "target_block_id": {"type": "int", "description": "Index of memory block"},
            "tactic": {"type": "string", "values": ["evict", "retain"]},
        },
    },
    "medium": {
        "name": "medium",
        "difficulty": "medium",
        "description": "Reduce VRAM below 40% while preserving important context blocks.",
        "action_schema": {
            "target_block_id": {"type": "int", "description": "Index of memory block"},
            "tactic": {
                "type": "string",
                "values": ["evict", "retain", "compress"],
            },
        },
    },
    "hard": {
        "name": "hard",
        "difficulty": "hard",
        "description": "Handle RAG spikes under tight capacity with priority-aware control.",
        "action_schema": {
            "target_block_id": {"type": "int", "description": "Index of memory block"},
            "tactic": {
                "type": "string",
                "values": ["evict", "retain", "compress"],
            },
            "priority": {
                "type": "int",
                "values": [1, 2, 3, 4, 5],
                "description": "Hard-task priority signal (1=lowest importance, 5=highest)",
            },
        },
    },
}
