import asyncio
import json
from typing import Any, Dict, Optional

import websockets

from ai01.utils import logger


class SocketClient:
    """
    Handles all the websocket related operations
    """

    def __init__(
        self,
        url: str,
        headers: Dict[str, str],
        loop: asyncio.AbstractEventLoop,
        json: bool = True,
    ):
        # URL is the WebSocket server URL.
        self.url = url

        # Headers to be sent with the WebSocket request.
        self.headers = headers

        # Event loop to use for async operations.
        self.loop = loop

        # WebSocket connection instance.
        self.__ws: Optional[websockets.WebSocketClientProtocol] = None

        # Logger for SocketClient.
        self._logger = logger.getChild("socketClient")

        # JSON flag to determine if the messages are JSON or not.
        self.json = json

    @property
    def ws(self) -> websockets.WebSocketClientProtocol:
        # Get the WebSocket connection, raising an error if not connected.
        if self.__ws is None:
            raise Exception("WebSocket is not connected")
        return self.__ws

    @property
    def connected(self) -> bool:
        # Return the connection status of the WebSocket.
        return self.__ws is not None and self.__ws.open

    async def connect(self):
        """
        Connect to the WebSocket server.
        """
        try:            
            self.__ws = await websockets.connect(self.url, extra_headers=self.headers)            
        except Exception as e:
            self._logger.error(f"Error connecting to WebSocket: {e}")
            raise

    async def send(self, message: Any):
        """
        Send a message to the WebSocket server.
        """
        try:
            if not self.__ws:
                raise Exception("WebSocket is not connected")

            dump_data = json.dumps(message) if self.json else message

            await self.__ws.send(dump_data)

            return

        except Exception as e:
            self._logger.error(f"Error sending message: {e}")
            raise

    def close(self):
        """
        Close the WebSocket connection.
        """
        if self.__ws:
            self._logger.info("Closing WebSocket connection")
            self.loop.create_task(self.__ws.close())
