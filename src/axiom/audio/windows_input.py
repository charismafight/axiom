"""Windows-default microphone input using sounddevice and SoXR."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from axiom.audio.io import AudioFrame


MODEL_SAMPLE_RATE = 16_000
_CAPTURE_SAMPLE_WIDTH_BYTES = 4
_MODEL_SAMPLE_WIDTH_BYTES = 2
_MODEL_BLOCK_SAMPLES = 1_280
_MODEL_BLOCK_BYTES = _MODEL_BLOCK_SAMPLES * _MODEL_SAMPLE_WIDTH_BYTES
_QUEUE_BLOCKS = 8


class AudioInputError(RuntimeError):
    """Raised when the Windows default microphone stream cannot continue."""


@dataclass(frozen=True, slots=True)
class _NativeAudioChunk:
    pcm: bytes
    frames: int


class WindowsDefaultAudioInput:
    """Capture the Windows default format and adapt it for wake-word inference."""

    def __init__(self) -> None:
        self._stream: Any | None = None
        self._queue: asyncio.Queue[_NativeAudioChunk | AudioInputError] | None = None
        self._resampler: Any | None = None
        self._numpy: Any | None = None
        self._capture_sample_rate: float | None = None
        self._capture_channels: int | None = None
        self._failure: AudioInputError | None = None
        self._pending_model_pcm = bytearray()
        self._frames_active = False

    @property
    def capture_sample_rate(self) -> float | None:
        """Return the default input stream's negotiated sample rate."""
        return self._capture_sample_rate

    @property
    def capture_channels(self) -> int | None:
        """Return the number of channels exposed by the default input stream."""
        return self._capture_channels

    async def __aenter__(self) -> WindowsDefaultAudioInput:
        if self._stream is not None:
            raise AudioInputError("The Windows default microphone stream is already open.")

        try:
            import numpy as np
            import sounddevice as sd
            import soxr
        except (ImportError, OSError) as error:
            raise AudioInputError(
                'The audio runtime is missing. Install Axiom with the "audio" extra.'
            ) from error

        loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=_QUEUE_BLOCKS)
        self._failure = None
        self._pending_model_pcm.clear()
        self._numpy = np

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if getattr(status, "input_overflow", False):
                loop.call_soon_threadsafe(
                    self._fail,
                    AudioInputError("The microphone input stream overflowed."),
                )
                return
            if frames < 1:
                return

            pcm = bytes(indata)
            channels = self._capture_channels
            if channels is None:
                loop.call_soon_threadsafe(
                    self._fail,
                    AudioInputError("The microphone input format was not initialized."),
                )
                return
            expected_bytes = frames * channels * _CAPTURE_SAMPLE_WIDTH_BYTES
            if len(pcm) != expected_bytes:
                loop.call_soon_threadsafe(
                    self._fail,
                    AudioInputError(
                        f"The microphone returned {len(pcm)} PCM bytes; "
                        f"expected {expected_bytes}."
                    ),
                )
                return
            loop.call_soon_threadsafe(
                self._enqueue,
                _NativeAudioChunk(pcm=pcm, frames=frames),
            )

        stream: Any | None = None
        try:
            stream = sd.RawInputStream(
                samplerate=None,
                blocksize=0,
                device=None,
                channels=None,
                dtype="float32",
                latency="low",
                callback=callback,
            )
            capture_rate = float(stream.samplerate)
            capture_channels = int(stream.channels)
            if capture_rate <= 0 or capture_channels < 1:
                raise AudioInputError(
                    "The Windows default microphone returned an invalid audio format."
                )

            self._capture_sample_rate = capture_rate
            self._capture_channels = capture_channels
            self._resampler = soxr.ResampleStream(
                in_rate=capture_rate,
                out_rate=MODEL_SAMPLE_RATE,
                num_channels=capture_channels,
                dtype="float32",
                quality="HQ",
            )
            self._stream = stream
            stream.start()
        except Exception as error:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
            self._stream = None
            self._queue = None
            self._resampler = None
            self._numpy = None
            self._capture_sample_rate = None
            self._capture_channels = None
            if isinstance(error, AudioInputError):
                raise
            raise AudioInputError(
                f"Could not open the Windows default microphone input: {error}"
            ) from error

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
            self._resampler = None
            self._numpy = None
            self._capture_sample_rate = None
            self._capture_channels = None
            self._failure = None
            self._pending_model_pcm.clear()
            self._frames_active = False

    async def frames(self) -> AsyncIterator[AudioFrame]:
        """Yield 80 ms, mono, signed 16-bit PCM blocks at 16 kHz."""
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
                self._pending_model_pcm.extend(self._resample_to_model(item))
                while len(self._pending_model_pcm) >= _MODEL_BLOCK_BYTES:
                    pcm = bytes(self._pending_model_pcm[:_MODEL_BLOCK_BYTES])
                    del self._pending_model_pcm[:_MODEL_BLOCK_BYTES]
                    yield AudioFrame(
                        pcm=pcm,
                        sample_rate=MODEL_SAMPLE_RATE,
                        channels=1,
                        timestamp=time.monotonic(),
                    )
        finally:
            self._frames_active = False

    def _resample_to_model(self, chunk: _NativeAudioChunk) -> bytes:
        if (
            self._numpy is None
            or self._resampler is None
            or self._capture_channels is None
        ):
            raise AudioInputError("The microphone resampler is not initialized.")

        samples = self._numpy.frombuffer(chunk.pcm, dtype="<f4")
        expected_samples = chunk.frames * self._capture_channels
        if samples.size != expected_samples:
            raise AudioInputError(
                f"The microphone returned {samples.size} samples; "
                f"expected {expected_samples}."
            )

        samples = samples.reshape(chunk.frames, self._capture_channels)
        normalized = samples.astype(self._numpy.float32, copy=False)
        if self._capture_channels == 1:
            normalized = normalized[:, 0]

        resampled = self._resampler.resample_chunk(normalized)
        if resampled.ndim == 2:
            mono = resampled.mean(axis=1, dtype=self._numpy.float32)
        else:
            mono = resampled
        output = self._numpy.clip(
            self._numpy.rint(mono * 32768.0),
            -32768,
            32767,
        )
        return output.astype("<i2").tobytes()

    def _enqueue(self, chunk: _NativeAudioChunk) -> None:
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
        queue.put_nowait(chunk)

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
