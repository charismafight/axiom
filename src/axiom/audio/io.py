"""Open raw audio streams using the operating system's default devices."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class AudioBackendUnavailable(RuntimeError):
    """Raised when the configured audio backend cannot be imported."""


class AudioStreamError(RuntimeError):
    """Raised when a system-default audio stream cannot be opened."""


class DefaultAudioIO:
    """Create input and output streams without selecting hardware by name.

    Windows Sound Settings owns microphone and speaker selection. The
    ``device=None`` setting asks PortAudio to use the current system defaults.
    The returned streams are owned by the caller and can be used as context
    managers to ensure they stop and close cleanly. Stream callbacks run on the
    audio thread and should avoid blocking work.
    """

    def __init__(
        self,
        *,
        sample_rate: int = 48_000,
        input_channels: int = 1,
        output_channels: int = 1,
        blocksize: int = 0,
        dtype: str = "int16",
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")
        if input_channels <= 0 or output_channels <= 0:
            raise ValueError("input_channels and output_channels must be greater than zero")
        if blocksize < 0:
            raise ValueError("blocksize cannot be negative")

        self.sample_rate = sample_rate
        self.input_channels = input_channels
        self.output_channels = output_channels
        self.blocksize = blocksize
        self.dtype = dtype

    @staticmethod
    def _backend() -> Any:
        try:
            import sounddevice
        except (ImportError, OSError) as error:
            raise AudioBackendUnavailable(
                "The sounddevice audio backend is unavailable. "
                "Install Axiom with `python -m pip install -e .`."
            ) from error
        return sounddevice

    def open_input_stream(
        self,
        callback: Callable[..., None],
    ) -> Any:
        """Create a raw input stream from the current system default.

        Use the returned stream as a context manager to start and close it.
        The callback follows the ``sounddevice.RawInputStream`` signature.
        """
        backend = self._backend()
        try:
            return backend.RawInputStream(
                device=None,
                samplerate=self.sample_rate,
                channels=self.input_channels,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=callback,
            )
        except Exception as error:
            raise AudioStreamError(
                "Could not open the Windows default audio input stream. "
                "Check the selected input in Windows Sound Settings."
            ) from error

    def open_output_stream(
        self,
        callback: Callable[..., None],
    ) -> Any:
        """Create a raw output stream to the current system default.

        Use the returned stream as a context manager to start and close it.
        The callback follows the ``sounddevice.RawOutputStream`` signature.
        """
        backend = self._backend()
        try:
            return backend.RawOutputStream(
                device=None,
                samplerate=self.sample_rate,
                channels=self.output_channels,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=callback,
            )
        except Exception as error:
            raise AudioStreamError(
                "Could not open the Windows default audio output stream. "
                "Check the selected output in Windows Sound Settings."
            ) from error
