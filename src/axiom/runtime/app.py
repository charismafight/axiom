"""Device-independent resident wake-word runtime orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from axiom.audio import AudioFrame, AudioInput
from axiom.config import load_settings
from axiom.integrations.codex_desktop import VoiceShortcut
from axiom.runtime.state import RuntimeState, RuntimeStateMachine
from axiom.wakeword.assets import get_feature_assets_dir
from axiom.wakeword.engine import WakeWordEngine


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
    ) -> None:
        self.audio = audio
        self.wakeword = wakeword
        self.voice_shortcut = voice_shortcut
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
                        self.voice_shortcut.trigger()
                    finally:
                        self.wakeword.reset()

                    self.state.transition(RuntimeState.WAITING_FOR_WAKEWORD)
        finally:
            if self.state.state != RuntimeState.STOPPING:
                self.state.transition(RuntimeState.STOPPING)
            self.state.transition(RuntimeState.STOPPED)
            self._run_task = None

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
    """Raised until the device-dependent adapters are connected."""


def build_runtime() -> AxiomRuntime:
    """Create the configured runtime once concrete adapters are available."""
    try:
        settings = load_settings()
    except (OSError, ValueError) as error:
        raise RuntimeAdaptersPending(
            f"Axiom user configuration is invalid: {error}"
        ) from error

    pending = ["the Windows default microphone adapter is not connected"]
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

    raise RuntimeAdaptersPending(
        "Axiom cannot start yet: " + "; ".join(pending) + "."
    )
