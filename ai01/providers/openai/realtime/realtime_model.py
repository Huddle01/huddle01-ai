import asyncio
import base64
import json
import logging
import time
import uuid
from typing import Dict, Literal, Optional, Union

from aiortc.mediastreams import MediaStreamTrack

from ai01.agent import Agent
from ai01.rtc.utils import convert_to_audio_frame
from ai01.utils.emitter import EnhancedEventEmitter
from ai01.utils.socket import SocketClient

from . import _api, _exceptions
from .conversation import Conversation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealTimeModel(EnhancedEventEmitter[_api.EventTypes]):
    def __init__(self, agent: Agent, options: _api.RealTimeModelOptions):
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

        # Pending Responses which the Server will keep on generating.
        self._pending_responses : Dict[str, _api.RealtimeResponse] = {}

        # Conversation are all the Remote Tracks who are talking to the RealTimeModel.
        self._conversation: Conversation = Conversation(id = str(uuid.uuid4()))

        # Main Task is the Audio Append the RealTimeModel.
        self._main_tsk: Optional[asyncio.Future] = None

    def __str__(self):
        return f"RealTimeModel: {self._opts.model}"
    
    def __repr__(self):
        return f"RealTimeModel: {self._opts.model}"
    
    def add_track(self, track: MediaStreamTrack):
        """
        Add A Track, which needs to Communicate with the RealTimeModel.
        """
        self._conversation.add_track(track)

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

            await self._session_update()

            self._logger.info("Connected to OpenAI RealTime Model")

            self._main_tsk = asyncio.create_task(self._main(), name="RealTimeModel-Loop")

        except _exceptions.RealtimeModelNotConnectedError:
            raise 

        except Exception as e:
            self._logger.error(f"Error connecting to RealTime API: {e}")
            raise _exceptions.RealtimeModelSocketError()
    
    async def close(self):
        """
        Close the RealTimeModel.
        """
        self._conversation.stop()

        if self._main_tsk:
            self._main_tsk.cancel()

        self._logger.info("Closed RealTimeModel")

    async def truncate(self, *, item_id: str, content_index: int, audio_end_ms: int):
        """
        Truncate the Conversation Item, which tells the models about how much of the conversation to consider.
        """
        truncate_message: _api.ClientEvent.ConversationItemTruncate = {
            "item_id": item_id,
            "content_index": content_index,
            "audio_end_ms": audio_end_ms,
            "type": "conversation.item.truncate",
        }

        await self.socket.send(truncate_message)

    async def _session_update(self):
        """
        Updates the session on the OpenAI RealTime API.
        """
        try:
            self._logger.info("Send Session Updated")

            if not self.socket.connected:
                raise _exceptions.RealtimeModelNotConnectedError()

            opts = self._opts

            session_data: _api.ClientEvent.SessionUpdateData = {
                "instructions": self._opts.instructions,
                "voice": opts.voice,
                "input_audio_format": opts.input_audio_format,
                "input_audio_transcription": {"model": "whisper-1"},
                "max_response_output_tokens": self._opts.max_response_output_tokens,
                "modalities": opts.modalities,
                "temperature": opts.temperature,
                "tools": [],
                "turn_detection": opts.server_vad_opts,
                "output_audio_format": opts.output_audio_format,
                "tool_choice": opts.tool_choice,
            }

            payload: _api.ClientEvent.SessionUpdate = {
                "session": session_data,
                "type": "session.update",
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
        
    async def _handle_message(self, message: Union[str, bytes]):
        data = json.loads(message)

        event: _api.ServerEventType = data.get("type", "unknown")

        # Session Events
        if event == "session.created":
            self._handle_session_created(data)

        # Response Events
        elif event == "response.created":
            self._handle_response_created(data)
        elif event == "response.output_item.added":
            self._handle_response_output_item_added(data)
        elif event == "response.content_part.added":
            self._handle_response_content_part_added(data)
        elif event == "response.audio.delta":
            self._handle_response_audio_delta(data)
        elif event == "response.audio.done":
            self._handle_response_audio_done(data)
        elif event == "response.text.done":
            self._handle_response_text_done(data)
        elif event == "response.audio_transcript.done":
            self._handle_response_audio_transcript_done(data)
        elif event == "response.content_part.done":
            self._handle_response_content_part_done(data)
        elif event == "response.output_item.done":
            self._handle_response_output_item_done(data)
        elif event == "response.done":
            self._handle_response_done(data)

        # Input Audio Buffer Events, Append Events
        elif event == "input_audio_buffer.speech_started":
            self._handle_input_audio_buffer_speech_started(data)
        elif event == "input_audio_buffer.speech_stopped":
            self._handle_input_audio_buffer_speech_stopped(data)
        elif event == "response.audio_transcript.delta":
            self._handle_response_audio_transcript_delta(data)

        # Conversation Updated Events
        elif event == "conversation.item.created":
            self._handle_conversation_item_created(data)
        elif event == "conversation.item.truncated":
            self._handle_conversation_item_truncated(data)
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
        # elif event == "conversation.item.deleted":
        #     self._handle_conversation_item_deleted(data)


        elif event == "error":
            self._handle_error(data)
        else:
            self._logger.error(f"Unhandled Event: {event}")

    def _handle_response_output_item_done(self, data: dict):
        """
        Response Output Item Done is the Event Handler for the Response Output Item Done Event.
        """
        self._logger.info("Response Output Item Done", data)

    def _handle_response_content_part_done(self, data: dict):
        """
        Response Content Part Done is the Event Handler for the Response Content Part Done Event.
        """
        self._logger.info("Response Content Part Done", data)

    def _handle_conversation_item_truncated(self, data: dict):
        """
        Conversation Item Truncated is the Event Handler for the Conversation Item Truncated Event.
        """
        self._logger.info("Conversation Item Truncated")

    def _handle_conversation_item_deleted(self, data: dict):
        """
        Conversation Item Deleted is the Event Handler for the Conversation Item Deleted Event.
        """
        self._logger.info("Conversation Item Deleted", data)

    def _handle_conversation_item_created(self, data: _api.ServerEvent.ResponseCreated):
        """
        Conversation Item Created is the Event Handler for the Conversation Item Created Event.
        """
        self._logger.warning("IMPLEMENT!!! Conversation Item Created", data)

    def _handle_session_created(self, data: dict):
        """
        Session Created is the Event Handler for the Session Created Event.
        """
        self._logger.info("Session Created", data)
    
    def _handle_error(self, data: dict):
        """
        Error is the Event Handler for the Error Event.
        """
        self._logger.error(f"Error: {data}")

    def _handle_input_audio_buffer_speech_started(self, speech_started: _api.ServerEvent.InputAudioBufferSpeechStarted):
        """
        Speech Started is the Event Handler for the Speech Started Event.
        """
        self._logger.info("Speech Started")

        self.agent._update_state("listening")

        if self.agent.audio_track is not None and self.agent.audio_track.readyState == "live":
            audio_end_ms = int(self.agent.audio_track.audio_samples / (_api.SAMPLE_RATE * 1000))

            return asyncio.create_task(
                self.truncate(
                item_id=speech_started['item_id'],
                content_index=0,
                audio_end_ms=audio_end_ms,
                ), name="Truncate-Task"
            ) 

    def _handle_input_audio_buffer_speech_stopped(self, data: dict):
        """
        Speech Stopped is the Event Handler for the Speech Stopped Event.
        """
        self._logger.info("Speech Stopped", data)

    def _handle_input_audio_buffer_speech_committed(self, data: dict):
        """
        Speech Committed is the Event Handler for the Speech Committed Event.
        """
        self._logger.info("Speech Committed", data)

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
        self._logger.info("Response Done", data)

    def _handle_response_created(self, reponse_created: _api.ServerEvent.ResponseCreated):
        """
        Response Created is the Event Handler for the Response Created Event.
        """
        self._logger.info("✅ Response Created")

        response = reponse_created['response']
        
        status_details = response.get("status_details")
        usage = response.get("usage")

        new_response = _api.RealtimeResponse(
            id = response['id'],
            done_fut=asyncio.Future(),
            output=[],
            status=response['status'],
            status_details=status_details,
            usage=usage,
            created_timestamp=time.time(),
        )

        self._pending_responses[response['id']] = new_response

        self.emit('response_created', new_response)


    def _handle_response_output_item_added(self, output_item: _api.ServerEvent.ResponseOutputItemAdded):
        """
        Response Output Item Added is the Event Handler for the Response Output Item Added Event.
        """
        self._logger.info("✅ Response Output Item Added")
        
        response_id = output_item['response_id']
        response = self._pending_responses[response_id]
        done_fut = asyncio.Future()

        item_data = output_item['item']

        item_type: Literal['message', 'function_call'] = item_data['type'] # type: ignore
        
        item_rol: _api.Role = item_data.get('role', "assistane")

        new_output = _api.RealtimeOutput(
            response_id=response_id,
            item_id=item_data['id'],
            output_index=output_item['output_index'],
            type=item_type,
            role=item_rol,
            done_fut=done_fut,
            content=[]
        )

        response.output.append(new_output)

        self.emit('response_output_added', new_output)

    def _handle_response_content_part_added(self, content_added: _api.ServerEvent.ResponseContentPartAdded):
        """
        Response Content Part Added is the Event Handler for the Response Content Part Added Event.
        """
        self._logger.info("✅ Response Content Part Added")
        response_id = content_added['response_id']
        response = self._pending_responses[response_id]

        output_index = content_added['output_index']

        output = response.output[output_index]

        content_type = content_added['part']['type']

        new_content = _api.RealtimeContent(
            response_id=response_id,
            item_id=output.item_id,
            output_index=output_index,
            content_index=content_added['content_index'],
            text="",
            tool_calls=[],
            content_type=content_type,
            audio=[]
        )

        output.content.append(new_content)

        response.first_token_timestamp = time.time()

        self.emit('response_content_added', new_content)

    def _handle_response_audio_delta(self, response_audio_delta: _api.ServerEvent.ResponseAudioDelta):
        """
        Response Audio Delta is the Event Handler for the Response Audio Delta Event.
        """
        self._logger.info("✅ Response Audio Delta")

        response = self._pending_responses[response_audio_delta["response_id"]]
        output = response.output[response_audio_delta["output_index"]]
        content = output.content[response_audio_delta["content_index"]]

        data = base64.b64decode(response_audio_delta["delta"])

        audio = convert_to_audio_frame(
            data=data,
            sample_rate=_api.SAMPLE_RATE,
            num_channels=_api.NUM_CHANNELS,
            samples_per_channel=len(data) // 2,
        )

        content.audio.append(audio)

        if track := self.agent.audio_track:
            track.enqueue_audio(
                content_index=content.content_index,
                audio=audio,
            )

    def _handle_response_audio_transcript_delta(self, response_audio_delta: _api.ServerEvent.ResponseAudioTranscriptDelta):
        """
        Response Audio Transcript Delta is the Event Handler for the Response Audio Transcript Delta Event.
        """
        self._logger.info("Response Audio Transcript Delta")

    def _handle_response_audio_done(self, data: dict):
        """
        Response Audio Done is the Event Handler for the Response Audio Done Event.
        """
        self._logger.info("✅ Response Audio Done", data)

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

    async def _main(self):
        """
            Runs the Main Loop for the RealTimeModel.
        """
        if not self.socket.connected:
            raise _exceptions.RealtimeModelNotConnectedError()
        
        try:
            async def handle_audio_chunk():
                while self._conversation.active:

                    if audio_chunk := self._conversation.recv():
                        await self._send_audio_append(audio_chunk)
                        continue

                    await asyncio.sleep(0.01)

            self._main_tsk = asyncio.create_task(handle_audio_chunk(), name="RealTimeModel-AudioAppend")
        except Exception as e:
            self._logger.error(f"Error in Main Loop: {e}")
