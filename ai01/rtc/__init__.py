from huddle01 import Role
from huddle01.local_peer import ProduceOptions
from huddle01.room import RoomEvents, RoomEventsData

from .audio_resampler import AudioFrame, AudioResampler
from .rtc import RTC, HuddleClientOptions, RTCOptions

__all__ = [
    "RTC",
    "RTCOptions",
    "AudioResampler",
    "AudioFrame",
    "HuddleClientOptions",
    "Role",
    "RoomEvents",
    "RoomEventsData",
    "ProduceOptions",
]


# Cleanup docs of unexported modules
_module = dir()
NOT_IN_ALL = [m for m in _module if m not in __all__]

__pdoc__ = {}

for n in NOT_IN_ALL:
    __pdoc__[n] = False
