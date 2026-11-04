"""Local wake-word engine contract."""

from __future__ import annotations

from typing import Protocol

from axiom.audio import AudioFrame


class WakeWordEngine(Protocol):
    """Consume microphone frames and detect the configured wake phrase."""

    def process_frame(self, frame: AudioFrame) -> bool:
        """Return True when the wake phrase is detected in the frame."""
        ...

    def reset(self) -> None:
        """Reset detector state after a conversation turn."""
        ...
