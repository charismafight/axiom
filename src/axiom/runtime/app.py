"""Device-independent resident wake-word runtime orchestration."""

from __future__ import annotations

import asyncio
import logging
import platform
from collections.abc import AsyncIterator

from axiom.audio import AudioFrame, AudioInput, WindowsDefaultAudioInput
from axiom.config import load_settings
from axiom.integrations.codex_desktop import VoiceShortcut
from axiom.integrations.windows_shortcut import InvalidShortcut, create_voice_shortcut
from axiom.runtime.state import RuntimeState, RuntimeStateMachine
from axiom.wakeword.assets import get_feature_assets_dir
from axiom.wakeword.engine import WakeWordEngine
from axiom.voice.feedback import (
    SilentWakeAcknowledgement,
    WakeAcknowledgement,
    WakeAcknowledgementError,
    WindowsWakeAcknowledgement,
)
from axiom.wakeword.openwakeword_engine import (
    WakeWordModelError,
    create_openwakeword_engine,
)


_LOGGER = logging.getLogger(__name__)


class AxiomRuntime:
    """Listen locally for the wake phrase and trigger Codex Desktop Voice.

    Codex owns the conversation audio after the configured shortcut is sent.
    The runtime awaits each input frame and does not poll in a busy loop.
    """

    def __init__(
        self,
        *,
        audio: AudioInput,
        wakeword: WakeWordEngine,
        voice_shortcut: VoiceShortcut,
        wake_acknowledgement: WakeAcknowledgement | None = None,
    ) -> None:
        self.audio = audio
        self.wakeword = wakeword
        self.voice_shortcut = voice_shortcut
        self.wake_acknowledgement = (
            wake_acknowledgement
            if wake_acknowledgement is not None
            else SilentWakeAcknowledgement()
        )
        self.state = RuntimeStateMachine()
        self._run_task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        """Keep the local wake-word listener active until cancelled or closed."""
        current_task = asyncio.current_task()
        if current_task is None:
            raise RuntimeError("AxiomRuntime.run must be called from an asyncio task")
        if self._run_task is not None and not self._run_task.done():
            raise RuntimeError("Axiom runtime is already running")

        self._run_task = current_task
        self.state.transition(RuntimeState.STARTING)
        try:
            async with self.audio:
                self.state.transition(RuntimeState.WAITING_FOR_WAKEWORD)
                frames: AsyncIterator[AudioFrame] = self.audio.frames().__aiter__()

                while True:
                    try:
                        frame = await anext(frames)
                    except StopAsyncIteration:
                        break

                    if not self.wakeword.process_frame(frame):
                        continue

                    self.state.transition(RuntimeState.TRIGGERING_CODEX_VOICE)
                    try:
                        await self._play_wake_acknowledgement(frames)
                    except WakeAcknowledgementError as error:
                        _LOGGER.warning("Wake acknowledgement unavailable: %s", error)
                    try:
                        self.voice_shortcut.trigger()
                    finally:
                        self.wakeword.reset()

                    self.state.transition(RuntimeState.WAITING_FOR_WAKEWORD)
        finally:
            if self.state.state != RuntimeState.STOPPING:
                self.state.transition(RuntimeState.STOPPING)
            self.state.transition(RuntimeState.STOPPED)
            self._run_task = None

    async def _play_wake_acknowledgement(
        self,
        frames: AsyncIterator[AudioFrame],
    ) -> None:
        playback = asyncio.create_task(self.wake_acknowledgement.play())
        loop = asyncio.get_running_loop()
        try:
            while not playback.done():
                try:
                    await anext(frames)
                except StopAsyncIteration:
                    break
            await playback

            settle_until = loop.time() + 0.25
            while loop.time() < settle_until:
                try:
                    await anext(frames)
                except StopAsyncIteration:
                    break
        finally:
            if not playback.done():
                playback.cancel()
                try:
                    await playback
                except asyncio.CancelledError:
                    pass

    async def stop(self) -> None:
        """Cancel the resident loop and wait for audio resources to close."""
        task = self._run_task
        if task is None or task is asyncio.current_task():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class RuntimeAdaptersPending(RuntimeError):
    """Raised when the runtime configuration or prerequisites are not ready."""


def build_runtime() -> AxiomRuntime:
    """Create the configured Windows-default microphone runtime."""
    try:
        settings = load_settings()
    except (OSError, ValueError) as error:
        raise RuntimeAdaptersPending(
            f"Axiom user configuration is invalid: {error}"
        ) from error

    pending: list[str] = []
    if platform.system() != "Windows":
        pending.append("the resident microphone and shortcut runtime requires Windows")
    if (
        settings.wakeword_model_path is None
        or not settings.wakeword_model_path.is_file()
    ):
        pending.append(
            "the custom Hey Axiom ONNX model is missing at "
            f"{settings.wakeword_model_path}"
        )
    else:
        feature_directory = get_feature_assets_dir(settings.wakeword_model_path)
        missing_features = [
            name
            for name in ("melspectrogram.onnx", "embedding_model.onnx")
            if not (feature_directory / name).is_file()
        ]
        if missing_features:
            pending.append(
                "shared wake-word feature assets are missing "
                f"({', '.join(missing_features)}); run axiom prepare-wakeword"
            )
    if not settings.codex_voice_shortcut:
        pending.append("the Codex Voice shortcut is not configured")

    if pending:
        raise RuntimeAdaptersPending("Axiom cannot start: " + "; ".join(pending) + ".")

    try:
        wakeword = create_openwakeword_engine(settings)
        voice_shortcut = create_voice_shortcut(settings.codex_voice_shortcut or "")
    except (WakeWordModelError, InvalidShortcut) as error:
        raise RuntimeAdaptersPending(f"Axiom runtime setup failed: {error}") from error

    return AxiomRuntime(
        audio=WindowsDefaultAudioInput(),
        wakeword=wakeword,
        voice_shortcut=voice_shortcut,
        wake_acknowledgement=WindowsWakeAcknowledgement(),
    )
