import logging
from typing import Optional

from pydantic import BaseModel

from ..rtc import RTC, RTCOptions
from ..rtc.audio_track import AudioTrack
from ..utils.emitter import EnhancedEventEmitter
from ._exceptions import RoomNotConnectedError, RoomNotCreatedError


class AgentOptions(BaseModel):
    """ "
    Every Agent is created with a set of options that define the configuration for the Agent.

    Args:
        rtc_options (RTCOptions): RTC Options for the Agent.
        audio_track (MediaStreamTrack): Audio Stream Track for the Agent.
    """

    rtc_options: RTCOptions
    """
    RTC Options is the configuration for the RTC.
    """

    audio_track: Optional[AudioTrack]
    """
    Audio Track is the Audio Stream Track for the Agent.
    """

    class Config:
        arbitrary_types_allowed = True


logger = logging.getLogger("Agent")


class Agent(EnhancedEventEmitter):
    """
    Agents is defined as the higher level user which is its own entity and has exposed APIs to
    interact with different Models and Outer World using dRTC.

    Agents can be connected to the dRTC Network by two stepsL
        - Joining the Agent to the dRTC Network, which assigns the Agent to a Room, using this Agent can setup event Listeners before connecting to the Room.
        - Connecting the Agent to the Room, which allows the Agent to send and receive data from the Room, and become part of the Room.
    """

    def __init__(self, options: AgentOptions):
        super(Agent, self).__init__()

        # Options is the configuration for the Agent.
        self.options = options

        # RTC is the Real Time Communication Handler for the Agent.
        self.__rtc = RTC(options.rtc_options)

        # Audio Track is the Audio Stream Track for the Agent.
        self.audio_track = options.audio_track

        # Logger for the Agent.
        self._logger = logger.getChild("Agent")

    @property
    def rtc(self):
        return self.__rtc

    @property
    def logger(self):
        return self._logger

    @property
    def room(self):
        """
        Room is the the abstraction under which every participant and the Agent is connected to, This is only available after the Agent is connected.

        raise ValueError if Agent is not connected to the Room.
        """
        if not self.__rtc.room:
            raise RoomNotCreatedError()

        return self.__rtc.room

    async def join(self):
        """
        Joins the dRTC Network and creates a Room instance for the Agent.

        This method establishes a connection to the dRTC Network and creates a Room instance for the agent.
        The returned Room object allows you to listen to events such as:
        - Remote peers joining or leaving the Room.
        - Room-specific events triggered during its lifecycle.

        Example Usage:
            ```python
            room = await agent.join()


            @room.on(RoomEvents.RoomJoined)
            def on_room_join():
                print("Room successfully joined!")
            ```
        """
        self.logger.info("Joining Agent to the dRTC Network")

        room = await self.__rtc.join()

        if not room:
            raise RoomNotConnectedError()

        return room

    async def connect(self):
        """
        Connects the Agent to the Room, This is only available after the Agent is joined to the dRTC Network.
        """
        self.logger.info("Connecting Agent to the Room")

        room = self.__rtc.room

        if not room:
            raise RoomNotCreatedError()

        await room.connect()
