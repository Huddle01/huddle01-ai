from typing import Any, Optional, TypedDict

from pydantic import BaseModel


class EventType(str):
    pass


class Events:
    class Connected(TypedDict):
        peer_id: str

    class Disconnected(TypedDict):
        peer_id: str

    class Speaking(TypedDict):
        peer_id: str

    class Listening(TypedDict):
        peer_id: str

    class Thinking(TypedDict):
        peer_id: str


class ToolCallData(BaseModel):
    function_name: str
    arguments: Optional[dict[str, Any]]


class ToolResponseData(BaseModel):
    result: dict
    end_of_turn: bool = False
