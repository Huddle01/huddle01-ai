import random
from typing import Dict, Optional, TypedDict


class ComplaintType(TypedDict):
    name: str
    complaint: str
    resolution_period: str


complaint_book: Dict[int, ComplaintType] = {
    1234: {
        "name": "Chad",
        "complaint": "chat in the app is not working",
        "resolution_period": "3 hours",
    },
    5678: {
        "name": "Brad",
        "complaint": "I am not able to login",
        "resolution_period": "2 days",
    },
}


def generate_complaint_id() -> int:
    """Generate a unique 4-digit complaint ID."""
    while True:
        complaint_id = random.randint(1000, 9999)
        if complaint_id not in complaint_book:
            return complaint_id


def add_complaint(name: str, complaint: str) -> int:
    """Store the name and complaint of a person in the complaint book.

    Args:
        name: Name of the person.
        complaint: Complaint of the person.

    Returns:
        The generated complaint ID.
    """
    # Generate a random resolution period for the complaint in days or hours
    if random.choice([True, False]):
        resolution_period = f"{random.randint(1, 7)} days"
    else:
        resolution_period = f"{random.randint(1, 24)} hours"

    complaint_id = generate_complaint_id()
    complaint_book[complaint_id] = ComplaintType(
        name=name, complaint=complaint, resolution_period=resolution_period
    )
    print(
        f"Stored the complaint of {name} as '{complaint}' with a resolution period of {resolution_period} and complaint ID {complaint_id}"
    )
    return complaint_id


add_complaint_tool: Dict = {
    "name": "add_complaint",
    "description": "Store the name and complaint of a person in the complaint book.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "Name of the person whose complaint is to be stored.",
            },
            "complaint": {"type": "STRING", "description": "Complaint of the person"},
        },
        "required": ["name", "complaint"],
    },
}


def get_complaint_details(complaint_id: int) -> Optional[ComplaintType]:
    """Get the complaint and resolution period of the complaint of a person from the complaint book.

    Args:
        complaint_id: Complaint ID of the person.

    Returns:
        The complaint and resolution period of the complaint, or None if the complaint ID is not found.
    """
    return complaint_book.get(complaint_id)


get_complaint_details_tool: Dict = {
    "name": "get_complaint_details",
    "description": "Get the complaint and resolution period of the complaint of a person from the complaint book",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "complaint_id": {
                "type": "INTEGER",
                "description": "Complaint ID of the person whose complaint is to be retrieved.",
            },
        },
        "required": ["complaint_id"],
    },
}
