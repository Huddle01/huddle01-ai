import asyncio
import os
import traceback

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

SEND_SAMPLE_RATE = 16000  # Sample rate for sending mic input
RECEIVE_SAMPLE_RATE = 24000  # Sample rate for audio output
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.0-flash-exp"

# Initialize the GenAI client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"api_version": "v1alpha"},
)

CONFIG = {"generation_config": {"response_modalities": ["AUDIO"]}}


class AudioLoop:
    def __init__(self):
        self.audio_in_queue = None  # Queue for audio we receive from Gemini
        self.audio_out_queue = None  # Queue for mic audio we send to Gemini
        self.session = None
        # A buffer to store leftover audio from bigger-than-requested chunks.
        self.play_buffer = bytearray()

    async def send_text(self):
        """Send user-entered text to the model."""
        while True:
            text = await asyncio.to_thread(input, "message > ")
            if text.lower() == "q":
                break
            await self.session.send(text or ".", end_of_turn=True)

    async def send_realtime(self):
        """Continuously send mic audio chunks to the model."""
        while True:
            msg = await self.audio_out_queue.get()
            await self.session.send(msg)

    async def listen_audio(self):
        """Capture microphone input and enqueue it to be sent to Gemini."""

        def callback(indata, frames, time, status):
            if status:
                print(f"Audio input error: {status}")
            try:
                self.audio_out_queue.put_nowait(
                    {"data": indata.copy().tobytes(), "mime_type": "audio/pcm"}
                )
            except asyncio.QueueFull:
                print("⚠️ Queue is full. Dropping mic audio chunk.")

        print("🎤 Listening... Press Ctrl+C to exit.")
        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                while True:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("🎤 Stopped listening to mic input.")

    async def receive_audio(self):
        """Receive audio chunks from Gemini and put them into the playback queue."""
        while True:
            turn = self.session.receive()
            async for response in turn:
                if response.data:
                    await self.audio_in_queue.put(response.data)
                elif response.text:
                    print(response.text, end="")

    def fill_outdata(self, outdata: np.ndarray):
        """
        Fill 'outdata' from our ring buffer.
        If we don't have enough audio in 'play_buffer', read from audio_in_queue.
        """
        bytes_needed = outdata.nbytes  # e.g., frames * channels * 2 bytes
        # If we don't have enough leftover audio in 'play_buffer', pull more from the queue.
        while len(self.play_buffer) < bytes_needed:
            try:
                # This call is non-blocking: if empty, it raises QueueEmpty
                new_chunk = self.audio_in_queue.get_nowait()
                self.play_buffer += new_chunk
            except asyncio.QueueEmpty:
                # No more audio available right now; fill the remainder with zeros.
                missing = bytes_needed - len(self.play_buffer)
                self.play_buffer += b"\x00" * missing
                break

        # Now we have at least 'bytes_needed' in the buffer (or we've zero-filled).
        chunk = self.play_buffer[:bytes_needed]
        self.play_buffer = self.play_buffer[bytes_needed:]

        # Convert chunk to int16 array and reshape to match (frames, channels).
        outdata[:] = np.frombuffer(chunk, dtype="int16").reshape(-1, 1)

    async def play_audio(self):
        """Play audio data from the ring buffer in the OutputStream callback."""

        def callback(outdata, frames, time, status):
            if status:
                print(f"Audio output error: {status}")
            self.fill_outdata(outdata)

        print("🎧 Playing audio responses...")
        try:
            with sd.OutputStream(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                while True:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("🎧 Stopped audio playback.")

    async def run(self):
        """Main loop to manage tasks and handle graceful exit."""
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                # Async queues
                self.audio_in_queue = asyncio.Queue()
                self.audio_out_queue = asyncio.Queue(maxsize=5)

                # Start tasks
                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                await send_text_task  # Wait for text input or 'q'
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            print("\nExiting...")
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    try:
        main = AudioLoop()
        asyncio.run(main.run())
    except KeyboardInterrupt:
        print("\nExiting... Goodbye!")
