import random
from typing import Dict, TypedDict


class ComplaintType(TypedDict):
    complaint: str
    resolution_period: str


complaint_book: dict[str, ComplaintType] = {
    "Arush": {
        "complaint": "chat in the app is not working",
        "resolution_period": "3 hours",
    },
    "Om": {"complaint": "I am not able to login", "resolution_period": "2 days"},
}


def check_for_complaint(name: str) -> bool:
    """Check if the name is already stored in the complaint book.

    Args:
        name: Name of the person.

    Returns:
        True if the name is already stored, False otherwise.
    """
    return name in complaint_book


check_for_complaint_tool: Dict = {
    "name": "check_for_complaint",
    "description": "Checks if the name is already stored in the complaint book.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "Name of the person to check in the complaint book.",
            }
        },
        "required": ["name"],
    },
}


def add_complaint(name: str, complaint: str) -> None:
    """Store the name and complaint of a person in the complaint book.

    Args:
        name: Name of the person.
        complaint: Complaint of the person.
    """
    # Generate a random resolution period for the complaint in days or hours
    if random.choice([True, False]):
        resolution_period = f"{random.randint(1, 7)} days"
    else:
        resolution_period = f"{random.randint(1, 24)} hours"

    complaint_book[name] = ComplaintType(
        complaint=complaint, resolution_period=resolution_period
    )
    print(
        f"Stored the complaint of {name} as '{complaint}' with a resolution period of {resolution_period}"
    )
    return None


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


def get_complaint_details(name: str) -> ComplaintType | None:
    """Get the complaint and resolution period of the complaint of a person from the complaint book.

    Args:
        name: Name of the person.

    Returns:
        The complaint and resolution period of the complaint, or an error message if the name is not found.
    """
    if check_for_complaint(name):
        return complaint_book[name]
    else:
        return None


get_complaint_details_tool: Dict = {
    "name": "get_complaint_details",
    "description": "Get the complaint and resolution period of the complaint of a person from the complaint book",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "Name of the person whose complaint is to be retrieved.",
            },
        },
        "required": ["name"],
    },
}
