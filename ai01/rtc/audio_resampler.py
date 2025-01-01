from typing import Literal

from av import AudioFrame
from av import AudioResampler as Resampler
from av.audio.fifo import AudioFifo


class AudioResampler:
    """
    Audio Resampler is used to resample the audio to the desired format, and store it in the Audio FIFO Buffer.
    Using the `resample` method, you can resample the audio frame to the desired format, and using the `recv` method, you can get the resampled audio frame.
    """

    def __init__(
        self, format: Literal["s16"], layout: Literal["mono", "stereo"], rate: int
    ):
        self.audio_fifo = AudioFifo()
        """
        Audio FIFO Buffer for the Audio Resampler.
        """

        self.resampler = Resampler(
            format=format,
            layout=layout,
            rate=rate,
        )
        """
        For the Audio Resampling, which is used to resample the audio to the desired format.
        """

    def resample(self, audio_frame: AudioFrame):
        """
        Resample the audio frame to the desired format, and add it to the Audio FIFO
        You can use the `recv` method to get the resampled audio frame.
        """
        resampled_frames = self.resampler.resample(audio_frame)

        for frame in resampled_frames:
            self.audio_fifo.write(frame)

    def recv(self) -> None | bytes:
        """
        Receive the audio frame from the Audio Resampler, which are stored in the Audio FIFO Queue.
        """
        frame = self.audio_fifo.read()

        if frame is None:
            return None

        pcm_data = frame.to_ndarray()

        pcm_bytes = pcm_data.tobytes()

        return pcm_bytes

    def clear(self):
        """
        Clear the Audio FIFO Buffer.
        """
        self.audio_fifo.clear()
