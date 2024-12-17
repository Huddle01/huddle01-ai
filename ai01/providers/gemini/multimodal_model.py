from asyncio.taskgroups import TaskGroup
import uuid
from google import genai
from pydantic.v1.main import BaseModel
from ai01.agent.agent import Agent
from ai01.providers.gemini.conversation import Conversation
from ...utils.emitter import EnhancedEventEmitter
import logging
import asyncio

from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiModalModelOptions(BaseModel):
    """
    MultiModalModelOptions is the configuration for the MultiModalModel
    """

    gemini_api_key:str
    """
    Gemini API Key is the API Key for the Gemini Provider
    """

    model = "gemini-2.0-flash-exp"
    """
    Model is the Model which is going to be used by the MultiModalModel
    """

    config = types.LiveConnectConfig(
        response_modalities=["TEXT","AUDIO"]
        )

    """
    Config is the Config which the Model is going to use for the conversation
    """


    class Config:
        arbitrary_types_allowed = True


class MultiModalModel(EnhancedEventEmitter):
    def __init__(self, agent:Agent,options:MultiModalModelOptions):
        self._agent = agent
        self._options = options

        self.client = genai.Client(
            api_key=self._options.gemini_api_key,
            http_options={"api_version": "v1alpha"},
        )

        self.loop = asyncio.get_event_loop()

        self._logger = logger.getChild(f"MultiModalModel-{self._options.model}")

        self._conversation:Conversation = Conversation(id=str(uuid.uuid4()))

        self.session = None

    def __str__(self):
        return f"Gemini MultiModal: {self._options.model}"

    def __repr__(self):
        return f"Gemini MultiModal: {self._options.model}"

    def conversation(self):
        return self._conversation


    async def send_audio(self,audio_bytes:bytes):

        if self.session is None:
            raise Exception("Session is not connected")

        await self.session.send({"data": audio_bytes, "mime_type": "audio/pcm"})

    async def handle_response(self):
        while True:
            turn = await self.session.receive()
            async for response in turn:
                if response.data:
                    await self.emit("response",response.data)
                elif response.text:
                    print(response.text,end="",flush=True)
                elif response.image:
                    print(response.image,end="",flush=True)

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


    async def connect(self):
        try:
            async with (
                self.client.aio.live.connect(model=self._options.model,config=self._options.config) as session,
                asyncio.TaskGroup() as tg
            ):
                self.session = session


                tg.create_task(self.handle_response())

        except Exception as e:
            self._logger.error(f"Error in connecting to the Gemini Model: {e}")
            raise e
