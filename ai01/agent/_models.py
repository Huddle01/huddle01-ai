# AgentsEvents is the Enum for the different types of Events emitted by the Agent.
class AgentsEvents(str):
    Connected: str = "Connected"
    Disconnected: str = "Disconnected"
    Speaking: str = "Speaking"
    Listening: str = "Listening"
    Thinking: str = "Thinking"
    ToolCall: str = "ToolCall"
