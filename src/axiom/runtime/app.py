"""Device-independent resident runtime orchestration."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator

from axiom.audio import AudioFrame, AudioIO
from axiom.runtime.state import RuntimeState, RuntimeStateMachine
from axiom.voice.session import VoiceSession
from axiom.wakeword.engine import WakeWordEngine


class AxiomRuntime:
    """Run the wake-listen and conversation state loop.

    Concrete audio, wake-word, and voice-session adapters are injected later.
    The runtime waits asynchronously for each audio frame; it does not poll in
    a busy loop.
    """

    def __init__(
        self,
        *,
        audio: AudioIO,
        wakeword: WakeWordEngine,
        voice_session: VoiceSession,
        pre_roll_frames: int = 25,
    ) -> None:
        if pre_roll_frames < 0:
            raise ValueError("pre_roll_frames cannot be negative")
        self.audio = audio
        self.wakeword = wakeword
        self.voice_session = voice_session
        self.pre_roll_frames = pre_roll_frames
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
                pre_roll: deque[AudioFrame] = deque(maxlen=self.pre_roll_frames)

                while True:
                    try:
                        frame = await anext(frames)
                    except StopAsyncIteration:
                        break

                    pre_roll.append(frame)
                    if not self.wakeword.process_frame(frame):
                        continue

                    self.state.transition(RuntimeState.CONVERSING)
                    try:
                        await self.voice_session.run_turn(
                            input_frames=frames,
                            output=self.audio,
                            pre_roll=tuple(pre_roll),
                        )
                    finally:
                        self.wakeword.reset()

                    pre_roll.clear()
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
    raise RuntimeAdaptersPending(
        "Axiom's runtime structure is ready, but audio, wake-word, and voice "
        "adapters are not connected yet."
    )
