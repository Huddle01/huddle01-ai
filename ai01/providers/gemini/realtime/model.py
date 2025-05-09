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
from ai01.providers._api import ToolCallData, ToolResponseData
from ai01.providers.gemini.realtime.conversation import Conversation
from ai01.utils.emitter import EnhancedEventEmitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiConfig(BaseModel):
    """
    Config is the configuration for the Gemini Model

    Attributes:
    - tools: List[types.FunctionDeclaration] | None

    """
    tools: Optional[List[types.FunctionDeclaration]] = None

    class Config:
        arbitrary_types_allowed = True


class GeminiRealtimeResponse(types.LiveServerMessage):
    def __init__(self, server_response: types.LiveServerMessage):
        super().__init__(**server_response.model_dump())

    @property
    def interrupted(self):
        """
        Check if the response is interrupted
        """
        if self.server_content is None:
            return None
        
        return self.server_content.interrupted


    @property
    def turn_complete(self) -> bool | None:
        """
        Check if the response is turn complete
        """
        if self.server_content is None:
            return None
    
        return self.server_content.turn_complete
    
    @property
    def model_turn(self) -> types.Content | None:
        """
        Get the model turn
        """
        if self.server_content is None:
            return None
        
        return self.server_content.model_turn
    
    @property
    def audio(self):
        """
        Get the audio response
        """
        return self.data
    
    def __repr__(self) -> str:
        return f"<GeminiRealtimeResponse model_turn={self.model_turn} interrupted={self.interrupted} turn_complete={self.turn_complete}>"



class GeminiOptions(BaseModel):
    """
    realtimeModelOptions is the configuration for the realtimeModel
    """

    gemini_api_key: str
    """
    Gemini API Key is the API Key for the Gemini Provider
    """

    model = "gemini-2.0-flash-live-001"
    """
    Model is the Model which is going to be used by the realtimeModel
    """

    system_instruction: Optional[str] = (
        "You are a Helpul Voice Assistant. You can help me with my queries."
    )

    response_modalities: Optional[List[types.Modality]] = ["AUDIO"]

    config: Optional[GeminiConfig] = None

    """
    Config is the Config which the Model is going to use for the conversation
    """

    class Config:
        arbitrary_types_allowed = True


class GeminiRealtime(EnhancedEventEmitter):
    def __init__(self, agent: Agent, options: GeminiOptions):
        super().__init__()
        
        self.agent = agent
        self._options = options

        tools: types.ToolDict = types.ToolDict()

        if options.config is not None:
            if options.config.tools is not None:
                tools.function_declarations = options.config.tools # type: ignore

        system_instruction_content = types.Content(
            parts=[types.Part(text=options.system_instruction)]
        )

        self.config: types.LiveConnectConfigDict = {
            "response_modalities": self._options.response_modalities,
            "realtime_input_config": {
                "automatic_activity_detection": {
                    "disabled": False,
                    "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
                    "end_of_speech_sensitivity": "END_SENSITIVITY_HIGH",
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                }
            },
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": "Kore",
                    }
                }
            },
            "system_instruction": system_instruction_content, # type: ignore
            "tools": [tools]
        }

        self.client = genai.Client(
            api_key=self._options.gemini_api_key,
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

    async def send_text(self, text: str, end_of_turn: bool = False):
        if self.session is None:
            raise Exception("Session is not connected")

        try:
            await self.session.send(input=text, end_of_turn=end_of_turn)
        except websockets.exceptions.ConnectionClosed:
            self._logger.warning("WebSocket connection closed while sending text.")
            self.session = None

    async def send_audio(self, audio_bytes: bytes):
        if self.session is None:
            raise Exception("Session is not connected")

        try:
            input = types.LiveClientRealtimeInput(
                media_chunks=[types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")]
            )
            await self.session.send(input=input, end_of_turn=False)
        except websockets.exceptions.ConnectionClosed:
            self._logger.warning("WebSocket connection closed while sending audio.")
            self.session = None

    async def handle_response(self):
        try:
            if self.session is None or self.agent.audio_track is None:
                raise Exception("Session or AudioTrack is not connected")
            while True:
                async for chunk in self.session.receive():
                    response = GeminiRealtimeResponse(server_response=chunk)
                    
                    if response.interrupted:
                        self._logger.info("Response interrupted")
                        self.agent.audio_track.flush_audio()

                    if response.audio:
                        self.agent.audio_track.enqueue_audio(response.audio)
                    elif response.text:
                        self.agent.emit(AgentsEvents.TextResponse, response.text)
                    elif response.tool_call:
                        if response.tool_call.function_calls is None:
                            continue

                        for function_call in response.tool_call.function_calls:
                            if function_call.name is None or function_call.id is None:
                                continue

                            async def callback(data: ToolResponseData):
                                if self.session is None:
                                    return

                                response = types.FunctionResponse(
                                    id=function_call.id,
                                    name=function_call.name,
                                    response=data.result,
                                )
                                await self.session.send(
                                    input=response, end_of_turn=data.end_of_turn
                                )

                            tool_call_data = ToolCallData(
                                function_name=function_call.name,
                                arguments=function_call.args,
                            )

                            self.agent.emit(
                                AgentsEvents.ToolCall, callback, tool_call_data
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
        """
        Run the Realtime Model and connect to the Gemini Model.
        This method will keep the connection alive and handle reconnections
        """
        while True:
            if self.tasks:
                for task in self.tasks:
                    if not task.done():
                        task.cancel()

                await asyncio.gather(*self.tasks, return_exceptions=True)

            self.tasks = []
            self.session = None

            try:
                self._logger.info(f"Connecting to the Gemini Model, {self._options.model}")

                async with self.client.aio.live.connect(
                    model=self._options.model, config=self.config
                ) as session:

                    self.session = session

                    handle_response_task = asyncio.create_task(self.handle_response())
                    fetch_audio_task = asyncio.create_task(self.fetch_audio_from_rtc())


                    self.tasks.extend([handle_response_task, fetch_audio_task])
                    await asyncio.gather(*self.tasks)

            except asyncio.CancelledError:
                self._logger.info("Realtime Model cancelled.")
                break

            except Exception as e:
                self._logger.error(f"Error in connecting to the Gemini Model: {e}")

            self.session = None
            await asyncio.sleep(5)
            
    async def connect(self):
        self.loop.create_task(self.run())
