import asyncio
import logging
import uuid

import websockets
from google import genai
from google.genai import types
from google.genai.live import AsyncSession
from pydantic.v1.main import BaseModel

from ai01.agent.agent import Agent
from ai01.providers.gemini.conversation import Conversation

from ...utils.emitter import EnhancedEventEmitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiModalModelOptions(BaseModel):
    """
    MultiModalModelOptions is the configuration for the MultiModalModel
    """

    gemini_api_key: str
    """
    Gemini API Key is the API Key for the Gemini Provider
    """

    model = "gemini-2.0-flash-exp"
    """
    Model is the Model which is going to be used by the MultiModalModel
    """

    config = types.LiveConnectConfig(response_modalities=["AUDIO"])

    """
    Config is the Config which the Model is going to use for the conversation
    """

    class Config:
        arbitrary_types_allowed = True


class MultiModalModel(EnhancedEventEmitter):
    def __init__(self, agent: Agent, options: MultiModalModelOptions):
        self.agent = agent
        self._options = options

        self.client = genai.Client(
            api_key=self._options.gemini_api_key,
            http_options={"api_version": "v1alpha"},
        )

        self.loop = asyncio.get_event_loop()

        self._logger = logger.getChild(f"MultiModalModel-{self._options.model}")

        self.conversation: Conversation = Conversation(id=str(uuid.uuid4()))

        self.session: AsyncSession | None = None

        self.tasks = []

    def __str__(self):
        return f"Gemini MultiModal: {self._options.model}"

    def __repr__(self):
        return f"Gemini MultiModal: {self._options.model}"

    async def send_audio(self, audio_bytes: bytes):
        if self.session is None:
            raise Exception("Session is not connected")

        try:
            await self.session.send({"data": audio_bytes, "mime_type": "audio/pcm"})
        except websockets.exceptions.ConnectionClosed:
            self._logger.warning("WebSocket connection closed while sending audio.")
            self.session = None

    async def handle_response(self):
        try:
            if self.session is None or self.agent.audio_track is None:
                raise Exception("Session or AudioTrack is not connected")
            while True:
                async for response in self.session.receive():
                    if response.data:
                        self.agent.audio_track.enqueue_audio(response.data)
                    elif response.text:
                        print(response.text, end="", flush=True)
        except websockets.exceptions.ConnectionClosedOK:
            self._logger.info("WebSocket connection closed normally.")
        except Exception as e:
            self._logger.error(f"Error in handle_response: {e}")
            raise e

    async def fetch_audio_from_rtc(self):
        while True:
            if not self.conversation.active:
                await asyncio.sleep(0.01)
                continue

            audio_chunk = self.conversation.recv()

            if audio_chunk is None:
                await asyncio.sleep(0.01)
                continue

            await self.send_audio(audio_chunk)

    async def run(self):
        while True:
            try:
                async with self.client.aio.live.connect(
                    model=self._options.model, config=self._options.config
                ) as session:
                    self.session = session

                    handle_response_task = asyncio.create_task(self.handle_response())
                    fetch_audio_task = asyncio.create_task(self.fetch_audio_from_rtc())

                    self.tasks.extend([handle_response_task, fetch_audio_task])
                    await asyncio.gather(*self.tasks)
            except Exception as e:
                self._logger.error(f"Error in connecting to the Gemini Model: {e}")
                await asyncio.sleep(5)  # Wait before attempting to reconnect

    async def connect(self):
        self.loop.create_task(self.run())
