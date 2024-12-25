from __future__ import annotations

import asyncio
import threading
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack
from av import AudioFrame
from av.audio.fifo import AudioFifo

from ai01 import rtc
from ai01.utils import logger

# Constants
AUDIO_PTIME = 0.020  # 20ms
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_CHANNELS = 1
DEFAULT_SAMPLE_WIDTH = 2

@dataclass
class AudioTrackOptions:
    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = DEFAULT_CHANNELS 
    sample_width: int = DEFAULT_SAMPLE_WIDTH

class AudioFIFOManager:
    def __init__(self):
        self.fifo = AudioFifo()
        self.lock = threading.Lock()
       
    @contextmanager
    def fifo_operation(self):
        with self.lock:
            yield self.fifo
           
    def flush(self):
        with self.lock:
            self.fifo = AudioFifo()

class AudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, options=AudioTrackOptions()):
        super().__init__()
        self.sample_rate = options.sample_rate
        self.channels = options.channels
        self.sample_width = options.sample_width # 2 bytes per sample (16-bit PCM)

        self._start = None
        self._timestamp = 0
        self.frame_samples = rtc.get_frame_size(self.sample_rate, AUDIO_PTIME)

        self._pushed_duration = 0.0
        self._total_played_time = None

        self.fifo_manager = AudioFIFOManager()

    def __repr__(self) -> str:
        return f"<AudioTrack kind={self.kind} state={self.readyState}> sample_rate={self.sample_rate} channels={self.channels} sample_width={self.sample_width}>" 

    @property 
    def audio_samples(self) -> int:
        """
        Audio Samples Returns the number of audio samples that have been played.
        """
        if self._total_played_time is not None:
            return int(self._total_played_time * self.sample_rate)
        queued_duration = self.fifo_manager.fifo.samples / self.sample_rate
        
        return int((self._pushed_duration - queued_duration) * self.sample_rate)

    def enqueue_audio(self, content_index:int, audio: AudioFrame):
        try:
            if self.readyState != "live":
                return MediaStreamError("AudioTrack is not live")
        
            with self.fifo_manager.fifo_operation() as fifo:
                fifo.write(audio)
                self._pushed_duration += audio.samples / self.sample_rate
        except Exception as e:
            logger.error(f"Error in enqueue_audio: {e}", exc_info=True)

    def flush_audio(self):
        """Flush the audio FIFO buffer"""
        self.fifo_manager.flush()

    async def recv(self) -> AudioFrame:
        if self.readyState != "live":
            raise MediaStreamError

        if self._start is None:
            self._start = asyncio.get_event_loop().time()
            self._timestamp = 0

        self._timestamp += self.frame_samples

        target_time = self._start + (self._timestamp / self.sample_rate)
        current_time = asyncio.get_event_loop().time()
        
        wait = target_time - current_time
        if wait > 0:
            await asyncio.sleep(wait)

        try:
            with self.fifo_manager.fifo_operation() as fifo:
                frame = fifo.read(self.frame_samples)

            if frame is None:
                silence_buffer = np.zeros(self.frame_samples, dtype=np.int16).tobytes()

                frame = rtc.convert_to_audio_frame(
                    silence_buffer,
                    self.sample_rate,
                    self.channels,
                    len(silence_buffer) // 2
                )

            frame.pts = self._timestamp
            
            self._total_played_time = self._timestamp / self.sample_rate

            return frame

        except Exception as e:
            logger.error(f"Error in recv: {e}", exc_info=True)
            raise MediaStreamError("Error processing audio frame")