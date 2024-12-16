import asyncio
import os

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# API Key and configuration
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
config = {"response_modalities": ["VOICE"]}
model = "models/gemini-2.0-flash-exp"

# Audio parameters
SAMPLE_RATE = 16000  # Sample rate in Hz
CHUNK_DURATION = 0.5  # Duration of each audio chunk in seconds
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)  # Number of samples per chunk


def read_audio():
    """
    Generator function to capture audio in chunks from the microphone.
    """

    def audio_callback(indata, frames, time, status):
        if status:
            print(f"Audio error: {status}")
        audio_queue.append(indata.copy())  # Append audio data to the queue

    audio_queue = []
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        callback=audio_callback,
        blocksize=CHUNK_SIZE,
    ):
        while True:
            if audio_queue:
                yield audio_queue.pop(0).tobytes()  # Convert audio chunk to bytes


async def audio_stream():
    """
    Async generator to yield audio chunks from the read_audio generator.
    """
    for data in read_audio():
        yield data


async def play_audio_chunk(audio_data):
    """
    Play audio chunks received from Gemini.
    """
    # Convert the audio data back to numpy array and play
    audio_array = np.frombuffer(audio_data, dtype="int16")
    sd.play(audio_array, samplerate=SAMPLE_RATE)
    sd.wait()  # Wait for playback to finish


async def main():
    print("Listening... Speak into the microphone. Type 'Ctrl+C' to exit.")
    async with client.aio.live.connect(model=model, config=config) as session:
        try:
            async for audio in session.start_stream(
                stream=audio_stream(), mime_type="audio/pcm"
            ):
                # Play back the audio response from Gemini
                await play_audio_chunk(audio.data)
        except KeyboardInterrupt:
            print("\nExiting...")


if __name__ == "__main__":
    asyncio.run(main())
