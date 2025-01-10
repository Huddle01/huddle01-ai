import asyncio
import base64
import json
import logging
import uuid
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel

from ai01.agent import Agent, AgentsEvents
from ai01.utils.socket import SocketClient

from ....utils.emitter import EnhancedEventEmitter
from . import _api, _exceptions
from .conversation import Conversation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealTimeModelOptions(BaseModel):
    """
    RealTimeModelOptions is the configuration for the RealTimeModel.
    """

    oai_api_key: str
    """
    OpenAI API Key is the API Key for the OpenAI API.
    """

    model: _api.RealTimeModels = "gpt-4o-realtime-preview-2024-12-17"
    """
    Model is the RealTimeModel to be used, defaults to gpt-4o-realtime-preview.
    """

    instructions: str = ""
    """
    Instructions is the Initial Prompt given to the Model.
    """

    modalities: list[_api.Modality] = ["text", "audio"]
    """
    Modalities is the list of things to be used by the Model.
    """

    voice: _api.Voice = "sage"
    """
    Voice is the of audio voices which will be generated and returned by the Model.
    """

    temperature: float = 0.8
    """
    Temperature is the randomness of the Model, to select the next token.
    """

    input_audio_format: _api.AudioFormat = "pcm16"
    """
    Input Audio Format is the format of the input audio, which is given to the Model.
    """

    output_audio_format: _api.AudioFormat = "pcm16"
    """
    Output Audio Format is the format of the audio, which is returned by the Model.
    """

    max_response_output_tokens: int | Literal["inf"] = 4096
    """
    Max Response Output Tokens is the maximum number of tokens in the response, defaults to 4096.
    """

    base_url: str = "wss://api.openai.com/v1/realtime"
    """
    Base URL is the URL of the RealTime API, defaults to the OpenAI RealTime API.
    """

    tool_choice: _api.ToolChoice = "auto"
    """
    Tools are different other APIs which the Model can access, defaults to auto.
    """

    function_declaration: List[Dict] = []
    """
    Function Declaration is the list of functions which can be used by the Model.
    """

    server_vad_opts: _api.ServerVad = {
        "type": "server_vad",
        "threshold": 0.5,
        "prefix_padding_ms": 1000,
        "silence_duration_ms": 500,
    }
    """
    Server VAD which means Voice Activity Detection is the configuration for the VAD, to detect the voice activity.
    """

    loop: Optional[asyncio.AbstractEventLoop] = None
    """
    Loop is the Event Loop to be used for the RealTimeModel, defaults to the current Event Loop.
    """

    class Config:
        arbitrary_types_allowed = True


class RealTimeModel(EnhancedEventEmitter):
    def __init__(self, agent: Agent, options: RealTimeModelOptions):
        # Agent is the instance which is interacting with the RealTimeModel.
        self.agent = agent

        self._opts = options
        # Loop is the Event Loop to be used for the RealTimeModel.
        self.loop = options.loop or asyncio.get_event_loop()

        # Socket is the WebSocket connection to the RealTime API.
        self.socket = SocketClient(
            url=f"{self._opts.base_url}?model={self._opts.model}",
            headers={
                "Authorization": f"Bearer {self._opts.oai_api_key}",
                "OpenAI-Beta": "realtime=v1",
            },
            loop=self.loop,
            json=True,
        )

        # Turn Detection is the configuration for the VAD, to detect the voice activity.
        self.turn_detection = options.server_vad_opts

        # Logger for RealTimeModel.
        self._logger = logger.getChild(f"RealTimeModel-{self._opts.model}")

        # Conversation is the Conversations which being are happening with the RealTimeModel.
        self._conversation: Conversation = Conversation(id=str(uuid.uuid4()))

        # Main Task is the Audio Append the RealTimeModel.
        self._main_tsk: Optional[asyncio.Future] = None

    def __str__(self):
        return f"RealTimeModel: {self._opts.model}"

    def __repr__(self):
        return f"RealTimeModel: {self._opts.model}"

    @property
    def conversation(self):
        return self._conversation

    async def connect(self):
        """
        Connects the RealTimeModel to the RealTime API.
        """
        try:
            self._logger.info(
                f"Connecting to OpenAI RealTime Model at {self._opts.base_url}"
            )

            await self.socket.connect()

            asyncio.create_task(self._socket_listen(), name="Socket-Listen")

            await self._session_create()

            self._logger.info("Connected to OpenAI RealTime Model")

            self._main_tsk = asyncio.create_task(
                self._main(), name="RealTimeModel-Main"
            )

        except _exceptions.RealtimeModelNotConnectedError:
            raise

        except Exception as e:
            self._logger.error(f"Error connecting to RealTime API: {e}")
            raise _exceptions.RealtimeModelSocketError()

    async def _session_create(self):
        """
        Session Updated is the Event Handler for the Session Update Event.
        """
        try:
            self._logger.info("Send Session Updated ")

            if not self.socket.connected:
                raise _exceptions.RealtimeModelNotConnectedError()

            opts = self._opts

            tools: List[Dict] = []

            def lowercase_type_values(d):
                for key, value in d.items():
                    if key == "type" and isinstance(value, str):
                        d[key] = value.lower()
                    elif isinstance(value, dict):
                        lowercase_type_values(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                lowercase_type_values(item)

            if opts.function_declaration:
                for tool in opts.function_declaration:
                    tool_dict = {"type": "function", **tool}
                    lowercase_type_values(tool_dict)
                    tools.append(tool_dict)

            session_data: _api.ClientEvent.SessionUpdateData = {
                "instructions": self._opts.instructions,
                "voice": opts.voice,
                "input_audio_format": opts.input_audio_format,
                "input_audio_transcription": {"model": "whisper-1"},
                "max_response_output_tokens": self._opts.max_response_output_tokens,
                "modalities": opts.modalities,
                "temperature": opts.temperature,
                "tools": tools,
                "turn_detection": opts.server_vad_opts,
                "output_audio_format": opts.output_audio_format,
                "tool_choice": opts.tool_choice,
            }

            payload: _api.ClientEvent.SessionUpdate = {
                "type": "session.update",
                "session": session_data,
            }

            await self.socket.send(payload)

        except Exception as e:
            self._logger.error(f"Error Sending Session Update Event: {e}")
            raise

    async def _send_audio_append(self, audio_byte: bytes):
        """
        Send Audio Append is the method to send the Audio Append Event to the RealTime API.
        """
        if not self.socket.connected:
            raise _exceptions.RealtimeModelNotConnectedError()

        pcm_base64 = base64.b64encode(audio_byte).decode("utf-8")

        payload: _api.ClientEvent.InputAudioBufferAppend = {
            "event_id": str(uuid.uuid4()),
            "type": "input_audio_buffer.append",
            "audio": pcm_base64,
        }

        await self.socket.send(payload)

    async def _socket_listen(self):
        """
        Listen to the WebSocket
        """
        try:
            if not self.socket.connected:
                raise _exceptions.RealtimeModelNotConnectedError()

            async for message in self.socket.ws:
                await self._handle_message(message)
        except Exception as e:
            logger.error(f"Error listening to WebSocket: {e}")

            raise _exceptions.RealtimeModelSocketError()

    async def _handle_message(self, message: Union[str, bytes]):
        data = json.loads(message)

        event: _api.ServerEventType = data.get("type", "unknown")

        if event == "session.created":
            self._handle_session_created(data)
        elif event == "error":
            self._handle_error(data)
        elif event == "input_audio_buffer.speech_started":
            self._handle_input_audio_buffer_speech_started(data)
        elif event == "input_audio_buffer.speech_stopped":
            self._handle_input_audio_buffer_speech_stopped(data)
        elif event == "response.audio_transcript.delta":
            self._handle_response_audio_transcript_delta(data)
        # elif event == "input_audio_buffer.committed":
        #     self._handle_input_audio_buffer_speech_committed(data)
        # elif (
        #     event == "conversation.item.input_audio_transcription.completed"
        # ):
        #     self._handle_conversation_item_input_audio_transcription_completed(
        #         data
        #     )
        # elif event == "conversation.item.input_audio_transcription.failed":
        #     self._handle_conversation_item_input_audio_transcription_failed(
        #         data
        #     )
        # elif event == "conversation.item.created":
        #     self._handle_conversation_item_created(data)
        # elif event == "conversation.item.deleted":
        #     self._handle_conversation_item_deleted(data)
        # elif event == "conversation.item.truncated":
        #     self._handle_conversation_item_truncated(data)
        # elif event == "response.created":
        #     self._handle_response_created(data)
        # elif event == "response.output_item.added":
        #     self._handle_response_output_item_added(data)
        # elif event == "response.content_part.added":
        #     self._handle_response_content_part_added(data)
        elif event == "response.audio.delta":
            self._handle_response_audio_delta(data)
        elif event == "response.function_call_arguments.done":
            self._handle_response_function_call_arguments_done(data)
        # elif event == "response.audio.done":
        #     self._handle_response_audio_done(data)
        # elif event == "response.text.done":
        #     self._handle_response_text_done(data)
        # elif event == "response.audio_transcript.done":
        #     self._handle_response_audio_transcript_done(data)
        # elif event == "response.content_part.done":
        #     self._handle_response_content_part_done(data)
        # elif event == "response.output_item.done":
        #     self._handle_response_output_item_done(data)
        # elif event == "response.done":
        #     self._handle_response_done(data)

        self._logger.info(f"Unhandled Event: {event}")

    def _handle_response_output_item_done(self, data: dict):
        """
        Response Output Item Done is the Event Handler for the Response Output Item Done Event.
        """
        self._logger.info("Response Output Item Done")

    def _handle_response_content_part_done(self, data: dict):
        """
        Response Content Part Done is the Event Handler for the Response Content Part Done Event.
        """
        self._logger.info("Response Content Part Done")

    def _handle_conversation_item_truncated(self, data: dict):
        """
        Conversation Item Truncated is the Event Handler for the Conversation Item Truncated Event.
        """
        self._logger.info("Conversation Item Truncated")

    def _handle_conversation_item_deleted(self, data: dict):
        """
        Conversation Item Deleted is the Event Handler for the Conversation Item Deleted Event.
        """
        self._logger.info("Conversation Item Deleted")

    def _handle_conversation_item_created(self, data: dict):
        """
        Conversation Item Created is the Event Handler for the Conversation Item Created Event.
        """
        self._logger.info("Conversation Item Created")

    def _handle_session_created(self, data: dict):
        """
        Session Created is the Event Handler for the Session Created Event.
        """
        self._logger.info("Session Created")

    def _handle_error(self, data: dict):
        """
        Error is the Event Handler for the Error Event.
        """
        self._logger.error(f"Error: {data}")

    def _handle_input_audio_buffer_speech_started(self, data: dict):
        """
        Speech Started is the Event Handler for the Speech Started Event.
        """
        self._logger.info("Speech Started")

        if self.agent.audio_track:
            self.agent.audio_track.flush_audio()

            self.agent.emit(AgentsEvents.Listening)

    def _handle_input_audio_buffer_speech_stopped(self, data: dict):
        """
        Speech Stopped is the Event Handler for the Speech Stopped Event.
        """
        self._logger.info("Speech Stopped")

    def _handle_input_audio_buffer_speech_committed(self, data: dict):
        """
        Speech Committed is the Event Handler for the Speech Committed Event.
        """
        self._logger.info("Speech Committed")

    def _handle_conversation_item_input_audio_transcription_completed(self, data: dict):
        """
        Input Audio Transcription Completed is the Event Handler for the Input Audio Transcription Completed Event.
        """
        self._logger.info("Input Audio Transcription Completed")

    def _handle_conversation_item_input_audio_transcription_failed(self, data: dict):
        """
        Input Audio Transcription Failed is the Event Handler for the Input Audio Transcription Failed Event.
        """
        self._logger.error("Input Audio Transcription Failed")

    def _handle_response_done(self, data: dict):
        """
        Response Done is the Event Handler for the Response Done Event.
        """
        self._logger.info("Response Done")

    def _handle_response_created(self, data: dict):
        """
        Response Created is the Event Handler for the Response Created Event.
        """
        self._logger.info("Response Created")

    def _handle_response_output_item_added(self, data: dict):
        """
        Response Output Item Added is the Event Handler for the Response Output Item Added Event.
        """
        self._logger.info("Response Output Item Added")

    def _handle_response_content_part_added(self, data: dict):
        """
        Response Content Part Added is the Event Handler for the Response Content Part Added Event.
        """
        self._logger.info("Response Content Part Added")

    def _handle_response_audio_delta(self, data: dict):
        """
        Response Audio Delta is the Event Handler for the Response Audio Delta Event.
        """
        self._logger.info("Response Audio Delta")

        base64_audio = data.get("delta")

        if base64_audio and self.agent.audio_track:
            self.agent.emit(AgentsEvents.Speaking)
            audio_bytes = base64.b64decode(base64_audio)
            self.agent.audio_track.enqueue_audio(audio_bytes=audio_bytes)

    def _handle_response_function_call_arguments_done(
        self, data: _api.ServerEvent.ResponseFunctionCallArgumentsDone
    ):
        """
        Response Function Call Arguments Done is the Event Handler for the Response Function Call Arguments Done Event.
        """

        call_id = data.get("call_id")

        async def callback(result: dict):
            response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "output": json.dumps(result),
                    "call_id": call_id,
                },
            }
            await self.socket.send(response)

        self.agent.emit(AgentsEvents.ToolCall, callback, data)

    def _handle_response_audio_transcript_delta(self, data: dict):
        """
        Response Audio Transcript Delta is the Event Handler for the Response Audio Transcript Delta Event.
        """
        self._logger.info("Response Audio Transcript Delta")

    def _handle_response_audio_done(self, data: dict):
        """
        Response Audio Done is the Event Handler for the Response Audio Done Event.
        """
        self._logger.info("Response Audio Done")

    def _handle_response_text_done(self, data: dict):
        """
        Response Text Done is the Event Handler for the Response Text Done Event.
        """
        self._logger.info("Response Text Done")

    def _handle_response_audio_transcript_done(self, data: dict):
        """
        Response Audio Transcript Done is the Event Handler for the Response Audio Transcript Done Event.
        """
        self._logger.info("Response Audio Transcript Done")

    async def _main(self):
        if not self.socket.connected:
            raise _exceptions.RealtimeModelNotConnectedError()

        try:

            async def handle_audio_chunk():
                while True:
                    if not self.conversation.active:
                        await asyncio.sleep(0.01)
                        continue

                    audio_chunk = self.conversation.recv()

                    if audio_chunk is None:
                        await asyncio.sleep(0.01)
                        continue

                    await self._send_audio_append(audio_chunk)

            self._main_tsk = asyncio.create_task(
                handle_audio_chunk(), name="RealTimeModel-AudioAppend"
            )
        except Exception as e:
            self._logger.error(f"Error in Main Loop: {e}")
