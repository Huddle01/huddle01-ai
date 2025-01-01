from typing import TypedDict


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
