import asyncio
import logging
import uuid
from typing import List, Optional

import websockets
from google import genai
from google.genai import types
from google.genai.live import AsyncSession
from pydantic.v1.main import BaseModel

from ai01.agent._models import AgentsEvents
from ai01.agent.agent import Agent
from ai01.providers.gemini.conversation import Conversation

from ...utils.emitter import EnhancedEventEmitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiConfig(BaseModel):
    function_declaration: Optional[List] = None
    retrieval: Optional[types.Retrieval] = None
    code_execution: Optional[types.ToolCodeExecution] = None
    google_search: Optional[types.GoogleSearch] = None
    google_search_retrieval: Optional[types.GoogleSearchRetrieval] = None

    class Config:
        arbitrary_types_allowed = True


class GeminiOptions(BaseModel):
    """
    realtimeModelOptions is the configuration for the realtimeModel
    """

    gemini_api_key: str
    """
    Gemini API Key is the API Key for the Gemini Provider
    """

    model = "gemini-2.0-flash-exp"
    """
    Model is the Model which is going to be used by the realtimeModel
    """

    system_instruction: Optional[str] = (
        "You are a Helpul Voice Assistant. You can help me with my queries."
    )

    config: GeminiConfig

    """
    Config is the Config which the Model is going to use for the conversation
    """

    class Config:
        arbitrary_types_allowed = True


class GeminiRealtime(EnhancedEventEmitter):
    def __init__(self, agent: Agent, options: GeminiOptions):
        self.agent = agent
        self._options = options

        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[
                    types.Part(
                        text=options.system_instruction,
                    )
                ]
            ),
            tools=[
                types.Tool(
                    # ignore the below error
                    function_declarations=options.config.function_declaration,
                    google_search=options.config.google_search,
                    google_search_retrieval=options.config.google_search_retrieval,
                    code_execution=options.config.code_execution,
                    retrieval=options.config.retrieval,
                )
            ],
        )

        self.client = genai.Client(
            api_key=self._options.gemini_api_key,
            http_options={"api_version": "v1alpha"},
        )

        self.loop = asyncio.get_event_loop()

        self._logger = logger.getChild(f"realtimeModel-{self._options.model}")

        self.conversation: Conversation = Conversation(id=str(uuid.uuid4()))

        self.session: AsyncSession | None = None

        self.tasks = []

    def __str__(self):
        return f"Gemini realtime: {self._options.model}"

    def __repr__(self):
        return f"Gemini realtime: {self._options.model}"

    async def send_audio(self, audio_bytes: bytes):
        if self.session is None:
            raise Exception("Session is not connected")

        try:
            input = types.LiveClientRealtimeInput(
                media_chunks=[types.Blob(data=audio_bytes, mime_type="audio/pcm")]
            )
            await self.session.send(input=input, end_of_turn=False)
        # {"data": audio_bytes, "mime_type": "audio/pcm"}, end_of_turn=False
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
                    elif response.tool_call:
                        print("tool call recieved", response.tool_call)
                        self.agent.emit(
                            AgentsEvents.ToolCall, self.session.send, response.tool_call
                        )

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
                    model=self._options.model, config=self.config
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
