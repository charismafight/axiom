"""Windows-default microphone input using sounddevice and PortAudio."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from axiom.audio.io import AudioFrame


_SAMPLE_RATE = 16_000
_CHANNELS = 1
_SAMPLE_WIDTH_BYTES = 2
_BLOCK_SIZE = 1_280
_QUEUE_BLOCKS = 8


class AudioInputError(RuntimeError):
    """Raised when the Windows default microphone stream cannot continue."""


class WindowsDefaultAudioInput:
    """Read fixed-size PCM frames from the Windows default input endpoint."""

    def __init__(self) -> None:
        self._stream: Any | None = None
        self._queue: asyncio.Queue[bytes | AudioInputError] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._failure: AudioInputError | None = None
        self._frames_active = False

    async def __aenter__(self) -> WindowsDefaultAudioInput:
        if self._stream is not None:
            raise AudioInputError("The Windows default microphone stream is already open.")

        try:
            import sounddevice as sd
        except (ImportError, OSError) as error:
            raise AudioInputError(
                'The audio runtime is missing. Install Axiom with the "audio" extra.'
            ) from error

        loop = asyncio.get_running_loop()
        self._loop = loop
        self._queue = asyncio.Queue(maxsize=_QUEUE_BLOCKS)
        self._failure = None

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if getattr(status, "input_overflow", False):
                loop.call_soon_threadsafe(
                    self._fail,
                    AudioInputError("The microphone input stream overflowed."),
                )
                return
            if frames != _BLOCK_SIZE:
                loop.call_soon_threadsafe(
                    self._fail,
                    AudioInputError(
                        f"The microphone returned {frames} samples; "
                        f"expected {_BLOCK_SIZE}."
                    ),
                )
                return

            pcm = bytes(indata)
            expected_bytes = _BLOCK_SIZE * _CHANNELS * _SAMPLE_WIDTH_BYTES
            if len(pcm) != expected_bytes:
                loop.call_soon_threadsafe(
                    self._fail,
                    AudioInputError(
                        f"The microphone returned {len(pcm)} PCM bytes; "
                        f"expected {expected_bytes}."
                    ),
                )
                return
            loop.call_soon_threadsafe(self._enqueue, pcm)

        stream: Any | None = None
        try:
            stream = sd.RawInputStream(
                samplerate=_SAMPLE_RATE,
                blocksize=_BLOCK_SIZE,
                device=None,
                channels=_CHANNELS,
                dtype="int16",
                latency="low",
                callback=callback,
            )
            stream.start()
        except Exception as error:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
            self._queue = None
            self._loop = None
            raise AudioInputError(
                f"Could not open the Windows default microphone input: {error}"
            ) from error

        self._stream = stream
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        stream, self._stream = self._stream, None
        try:
            if stream is not None:
                try:
                    stream.stop()
                finally:
                    stream.close()
        finally:
            self._queue = None
            self._loop = None
            self._failure = None
            self._frames_active = False

    async def frames(self) -> AsyncIterator[AudioFrame]:
        """Yield 80 ms, mono, signed 16-bit little-endian PCM blocks."""
        queue = self._queue
        if queue is None or self._stream is None:
            raise AudioInputError("Open the Windows default microphone before reading frames.")
        if self._frames_active:
            raise AudioInputError("Only one microphone frame iterator may be active.")

        self._frames_active = True
        try:
            while True:
                item = await queue.get()
                if isinstance(item, AudioInputError):
                    raise item
                yield AudioFrame(
                    pcm=item,
                    sample_rate=_SAMPLE_RATE,
                    channels=_CHANNELS,
                    timestamp=time.monotonic(),
                )
        finally:
            self._frames_active = False

    def _enqueue(self, pcm: bytes) -> None:
        queue = self._queue
        if queue is None or self._failure is not None:
            return
        if queue.full():
            self._fail(
                AudioInputError(
                    "Axiom could not process microphone audio in real time; "
                    "the input queue filled."
                )
            )
            return
        queue.put_nowait(pcm)

    def _fail(self, error: AudioInputError) -> None:
        if self._failure is not None:
            return
        self._failure = error
        queue = self._queue
        if queue is None:
            return
        while not queue.empty():
            queue.get_nowait()
        queue.put_nowait(error)
