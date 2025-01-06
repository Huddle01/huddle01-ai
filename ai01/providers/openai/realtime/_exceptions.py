from __future__ import annotations


class RealtimeModelError(Exception):
    """Base class for exceptions in this module."""

    message: str

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class RealtimeModelNotConnectedError(RealtimeModelError):
    """Exception raised for errors in the Realtime Model, when Model is not connected."""

    def __init__(
        self,
    ):
        super().__init__(
            """
            Model is not connected, Possible ways to fix this:
            - Call the `model.connect()` before calling any other method on the Model.
            - Make sure the API_KEY and Project_ID are valid before connecting to the Model.
            """
        )


class RealtimeModelSocketError(RealtimeModelError):
    """Exception raised for errors in the Realtime Model, when Socket Connection Errored"""

    def __init__(
        self,
    ):
        super().__init__(
            """
            Socket Connection Error, Possible ways to fix this:
            - Check the network connection and try again.
            - Make sure the RealTime API is up and running.
            """
        )


class RealtimeModelTrackInvalidError(RealtimeModelError):
    """Exception raised for errors in the Realtime Model, when Track is invalid"""

    def __init__(
        self,
    ):
        super().__init__(
            """
            Track is invalid, Possible ways to fix this:
            - Make sure the Track is of type `audio`.
            - Make sure the Track is not None.
            """
        )
