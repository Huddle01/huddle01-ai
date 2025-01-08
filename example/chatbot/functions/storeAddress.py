from typing import Dict

address_book: dict[str, str] = {}


def check_for_complaint(name: str) -> bool:
    """Check if the name is already stored in the complaint book.

    Args:
        name: Name of the person.

    Returns:
        True if the name is already stored, False otherwise.
    """
    return name in address_book


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


def add_complaint(name: str, address: str) -> None:
    """Store the name and address of a person in the complaint book.

    Args:
        name: Name of the person.
        address: City or State or Country Name.
    """
    address_book[name] = address
    print(f"Stored the address of {name} as {address}")
    return None


add_complaint_tool: Dict = {
    "name": "add_complaint",
    "description": "Store the name and address of a person in the complaint book.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "Name of the person whose address is to be stored.",
            },
            "address": {
                "type": "STRING",
                "description": "City, State, or Country Name to store for the person.",
            },
        },
        "required": ["name", "address"],
    },
}


def get_complaint_details(name: str) -> str:
    """Get the address of a person from the complaint book.

    Args:
        name: Name of the person.

    Returns:
        The address of the person, or an error message if the name is not found.
    """
    if check_for_complaint(name):
        return address_book[name]
    else:
        return f"Address not found for {name}"


get_complaint_details_tool: Dict = {
    "name": "get_complaint_details",
    "description": "Gets the address of a person from the complaint book.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "Name of the person whose address is to be retrieved.",
            }
        },
        "required": ["name"],
    },
}
