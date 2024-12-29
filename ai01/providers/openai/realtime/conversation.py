import asyncio
from typing import Dict

from aiortc.mediastreams import MediaStreamTrack

from ai01.utils import logger

from ....rtc.audio_resampler import AudioResampler
from . import _exceptions


class Conversation:
    def __init__(self, id: str):
        self.id = id
        """
        Conversation ID for the Realtime Conversation.
        """

        self.audio_resampler = AudioResampler(format="s16", layout="mono", rate=16000)
        """
        Audio Resampler for the Realtime Conversation, takes in Audio Frame and resamples it to the desired format.
        """

        self._logger = logger.getChild("Conversation")
        """
        Logger for the Conversation.
        """

        self._track_fut: Dict[str, asyncio.Future] = {}
        """
        Track Futures for different tracks.
        """

        self._active = True
        """
        Is the Conversation Active.
        """

    def __str__(self):
        return f"Conversation ID: {self.id}"
    
    def __repr__(self):
        return f"Conversation ID: {self.id}"
    
    @property
    def logger(self):
        return self._logger
    
    @property
    def active(self):
        return self._active
    
    def add_track(self, track: MediaStreamTrack):
        """
        Add a Track to the Conversation, which streamlines conversation into one Audio Stream.
        which can be later retrieved using the `recv` method and feeded to the Model.
        """
        if track.kind != "audio":
            raise _exceptions.RealtimeModelTrackInvalidError()
        
        track_id = track.id
        
        if self._track_fut.get(track_id):
            raise _exceptions.RealtimeModelError("Track is already started.")

        async def handle_track():
            try:
                while self._active and track.readyState != "ended":
                    frame = await track.recv()

                    frame_data = frame.to_ndarray()

                    logger.info(f"Received Frame: {frame_data}")
                    
                    frame.pts = None

                    if frame is None:
                        continue
                    
                    self.audio_resampler.resample(frame)

                if task := self._track_fut.get(track_id):
                    task.cancel()
                    del self._track_fut[track_id]

            except Exception as e:
                self.logger.error(f"Error in handling audio frame: {e}")

        self._track_fut[track_id] = asyncio.create_task(handle_track(), name=f"Conversation-{id}")

    def stop(self):
        """
        Stop the Conversation and clear the Audio FIFO Buffer.
        """
        self._active = False

        for task in self._track_fut.values():
            if not task.done():
                task.cancel()

        self._track_fut.clear()

        self.audio_resampler.clear()

    def recv(self):
        """
        Receive the resampled audio frame from the Audio Resampler.
        """
        return self.audio_resampler.recv()