"""Prerecorded wake acknowledgement playback through the Windows default output."""

from __future__ import annotations

import asyncio
import sys
from importlib.resources import as_file, files
from typing import Protocol


class WakeAcknowledgementError(RuntimeError):
    """Raised when Axiom cannot play its wake acknowledgement."""


class WakeAcknowledgement(Protocol):
    """Play the short acknowledgement used after a wake phrase is detected."""

    async def play(self) -> None:
        """Play the acknowledgement and return when playback finishes."""
        ...


class SilentWakeAcknowledgement:
    """No-op acknowledgement for runtimes constructed without Windows audio."""

    async def play(self) -> None:
        return None


class WindowsWakeAcknowledgement:
    """Play the bundled acknowledgement using the Windows default output device."""

    async def play(self) -> None:
        if sys.platform != "win32":
            raise WakeAcknowledgementError(
                "Wake acknowledgement playback is supported on Windows only."
            )

        import winsound

        asset = files("axiom.voice").joinpath("assets").joinpath(
            "wake_acknowledgement.wav"
        )
        try:
            with as_file(asset) as path:
                await asyncio.to_thread(
                    winsound.PlaySound,
                    str(path),
                    winsound.SND_FILENAME | winsound.SND_NODEFAULT,
                )
        except (OSError, RuntimeError) as error:
            raise WakeAcknowledgementError(
                f"Could not play the wake acknowledgement: {error}"
            ) from error
