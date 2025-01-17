import json
import logging

from huddle01 import (
    AccessToken,
    AccessTokenData,
    AccessTokenOptions,
    HuddleClient,
    HuddleClientOptions,
    Role,
)
from huddle01.handlers import ConsumeOptions
from huddle01.local_peer import ProduceOptions
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("RTC")


class RTCOptions(BaseModel):
    """
    RTCOptions is the configuration for the Room.
    """

    project_id: str
    """
    Project ID is the Huddle01 Project ID.
    """

    api_key: str
    """
    API Key is the Huddle01 API Key.
    """

    room_id: str
    """
    Room ID is the unique identifier of the Room.
    """

    huddle_client_options: HuddleClientOptions
    """
    Huddle Client Options is the configuration for the Huddle Client.
    """

    metadata: dict[str, str]
    """
    Metadata is the optional metadata for the Room.
    """

    role: str
    """
    Role is the role of the local user in the Room.
    """


class RTC:
    """
    RTC Handles anything related to Real Time Communication, using the dRTC Network,
    Currently it is using Huddle01 as the dRTC Network.
    """

    def __init__(self, options: RTCOptions):
        self._logger = logger.getChild(options.room_id)

        self._options = options

        self._huddle_client = HuddleClient(
            project_id=self._options.project_id,
            options=self._options.huddle_client_options,
        )

    def __str__(self):
        return f"RTC Room: {self._options.room_id}"

    def __repr__(self):
        return f"RTC Room: {self._options.room_id}"

    @property
    def options(self):
        return self._options

    @property
    def huddle_client(self):
        return self._huddle_client

    @property
    def room(self):
        return self._huddle_client.room

    async def produce(self, options: ProduceOptions):
        """
        Produces Media Stream Tracks to the Room.
        """
        local_peer = self.huddle_client.local_peer

        if not local_peer:
            raise ValueError(
                "Local Peer is not created, make sure to connect to the Room before producing."
            )

        await local_peer.produce(options=options)

    async def consume(self, peer_id: str, producer_id: str):
        """
        Consumes Media Stream Tracks from the Room.
        """
        local_peer = self.huddle_client.local_peer

        if not local_peer:
            raise ValueError(
                "Local Peer is not created, make sure to connect to the Room before consuming."
            )

        options = ConsumeOptions(producer_id=producer_id, producer_peer_id=peer_id)
        await local_peer.consume(options=options)

    async def join(self):
        """
        Joins the dRTC Network and creates a Room for the local user.

        This method establishes a connection to the dRTC Network and creates a Room instance for the local user.
        The returned Room object allows you to listen to events such as:
        - Remote peers joining or leaving the Room.
        - Room-specific events triggered during its lifecycle.

        Example Usage:
            ```python
            room = await rtc.join()


            @room.on(RoomEvents.RoomJoined)
            def on_room_join():
                print("Room successfully joined!")
            ```

        Parameters:
            None (all required options should be configured in `self._options`).

        Returns:
            Room: An instance representing the created Room, enabling event handling and interaction.

        Exceptions:
            Raises an Exception if there is an error while joining the Room.
            Common issues may include:
            - Invalid API key or room ID.
            - Network connectivity problems.
            - Issues during token generation or Room creation.

        Notes:
            - Ensure that `self._options` is correctly configured with the required fields:
                - `room_id`: The unique identifier of the Room.
                - `api_key`: Your Huddle01 API key.
                - `metadata`: Optional metadata for the Room (must be JSON serializable).
                - `role`: The role of the local user in the Room (e.g., "host", "guest").
        """
        self._logger.info("Join Huddle01 dRTC Network")

        accessTokenData = AccessTokenData(
            room_id=self._options.room_id,
            api_key=self._options.api_key,
            options=AccessTokenOptions(
                metadata=json.dumps(self._options.metadata),
            ),
            role=Role(self._options.role),
        )

        accessToken = AccessToken(
            data=accessTokenData,
        )

        try:
            token = await accessToken.to_jwt()

            room = await self.huddle_client.create(self._options.room_id, token)

            return room
        except Exception as e:
            logger.error("Error while joining the Room: ", e)
            raise e
