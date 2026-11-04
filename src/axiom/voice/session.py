"""Voice conversation session contract."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from axiom.audio import AudioFrame, AudioIO


class VoiceSession(Protocol):
    """Handle one spoken conversation and return when the turn is over."""

    async def run_turn(
        self,
        *,
        input_frames: AsyncIterator[AudioFrame],
        output: AudioIO,
        pre_roll: Sequence[AudioFrame],
    ) -> None:
        """Stream microphone audio and play replies until the turn ends."""
        ...
