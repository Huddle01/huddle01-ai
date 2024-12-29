import fractions
from typing import Union

import numpy as np
from av import AudioFrame

from ai01.utils import logger

AUDIO_PTIME = 0.020  # 20ms


def get_frame_size(sample_rate: int, ptime: float) -> int:
   """
   Frame size in samples, which is the number of samples in a frame.
   """
   return int(ptime * sample_rate)

def convert_to_audio_frame(
    data: Union[bytes, bytearray, memoryview],
    sample_rate: int,
    num_channels: int,
    samples_per_channel: int,
) -> AudioFrame:
    audio_array = np.frombuffer(data, dtype=np.int16)

    expected_length = num_channels * samples_per_channel  
    if len(audio_array) != expected_length:
        raise ValueError(f"Data length mismatch: got {len(audio_array)}, expected {expected_length}")

    if samples_per_channel != get_frame_size(sample_rate, AUDIO_PTIME):
        logger.warning("Unexpected frame duration")
        
    audio_array = audio_array.reshape(num_channels, samples_per_channel)
    frame = AudioFrame.from_ndarray(
        audio_array,
        format="s16", 
        layout="mono" if num_channels == 1 else "stereo"
    )
    frame.sample_rate = sample_rate
    frame.time_base = fractions.Fraction(1, sample_rate)
    return frame