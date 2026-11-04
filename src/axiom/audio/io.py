"""Device-independent audio contracts.

The Windows audio backend will implement these contracts after the target
hardware is available for integration work.
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


class AudioIO(Protocol):
    """Async audio input/output contract using Windows system defaults."""

    async def __aenter__(self) -> AudioIO:
        """Open the default input and output streams."""
        ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Stop streams and release audio resources."""
        ...

    def frames(self) -> AsyncIterator[AudioFrame]:
        """Yield microphone frames until the stream closes."""
        ...

    async def write_frame(self, frame: AudioFrame) -> None:
        """Play one PCM frame through the Windows default output."""
        ...
