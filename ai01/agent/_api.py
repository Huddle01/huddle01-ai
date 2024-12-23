from typing import Literal

AgentEventTypes = Literal[
    "listening",
    "speaking",
    "idle",
    "connected",
    "disconnected",
    "error",
]

AgentState = Literal[
    "speaking",
    "listening",
    "idle"
]