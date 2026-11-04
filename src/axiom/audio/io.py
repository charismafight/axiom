"""Device-independent microphone input contract.

The Windows audio backend will implement this contract after the target
hardware is available for integration work. Windows owns device selection.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AudioFrame:
    """One raw PCM frame delivered by an audio input backend."""

    pcm: bytes
    sample_rate: int
    channels: int
    timestamp: float


class AudioInput(Protocol):
    """Async microphone input contract using the Windows system default."""

    async def __aenter__(self) -> AudioInput:
        """Open the default microphone input stream."""
        ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Stop the input stream and release audio resources."""
        ...

    def frames(self) -> AsyncIterator[AudioFrame]:
        """Yield microphone frames until the stream closes."""
        ...
