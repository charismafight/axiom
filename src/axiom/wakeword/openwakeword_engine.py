"""Local wake-word adapter backed by an explicit custom openWakeWord model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from axiom.audio import AudioFrame
from axiom.config import AxiomSettings


class WakeWordModelError(RuntimeError):
    """Raised when the custom wake-word model cannot be initialized."""


class OpenWakeWordEngine:
    """Detect the configured phrase with a custom ONNX model on the CPU."""

    def __init__(
        self,
        *,
        model_path: Path,
        threshold: float = 0.5,
        patience: int = 2,
        model: Any | None = None,
    ) -> None:
        if model_path.suffix.casefold() != ".onnx":
            raise WakeWordModelError("The custom wake-word model must be an ONNX file.")
        if not model_path.is_file():
            raise WakeWordModelError(f"Wake-word model file not found: {model_path}")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if patience < 1:
            raise ValueError("patience must be a positive integer")

        self.model_path = model_path
        self.model_key = model_path.stem
        self.threshold = threshold
        self.patience = patience

        try:
            import numpy as np
        except ImportError as error:
            raise WakeWordModelError(
                "The wake-word runtime requires NumPy. Install Axiom with its wakeword extra."
            ) from error
        self._numpy = np
        self._pending_pcm = bytearray()

        if model is None:
            try:
                from openwakeword.model import Model
            except ImportError as error:
                raise WakeWordModelError(
                    "The openWakeWord runtime is missing. Install Axiom with its wakeword extra."
                ) from error

            try:
                model = Model(
                    wakeword_models=[str(model_path)],
                    inference_framework="onnx",
                )
            except Exception as error:
                raise WakeWordModelError(
                    f"Could not load the custom wake-word model at {model_path}: {error}"
                ) from error

        self._model = model

    def process_frame(self, frame: AudioFrame) -> bool:
        """Return True when the configured wake phrase crosses its threshold."""
        if frame.sample_rate != 16_000 or frame.channels != 1:
            raise ValueError("Wake-word input must be 16 kHz mono PCM.")
        if len(frame.pcm) % 2:
            raise ValueError("16-bit PCM frames must contain an even number of bytes.")

        self._pending_pcm.extend(frame.pcm)
        samples_per_prediction = 1_280
        bytes_per_prediction = samples_per_prediction * 2
        detected = False
        while len(self._pending_pcm) >= bytes_per_prediction:
            pcm = self._pending_pcm[:bytes_per_prediction]
            del self._pending_pcm[:bytes_per_prediction]
            samples = self._numpy.frombuffer(pcm, dtype="<i2")
            predictions = self._model.predict(
                samples,
                threshold={self.model_key: self.threshold},
                patience={self.model_key: self.patience},
            )
            if self.model_key not in predictions:
                raise WakeWordModelError(
                    f"The wake-word model did not return the expected score key "
                    f"'{self.model_key}'."
                )
            detected = detected or (
                float(predictions[self.model_key]) >= self.threshold
            )
        return detected

    def reset(self) -> None:
        """Clear the model's rolling audio and prediction buffers."""
        self._pending_pcm.clear()
        self._model.reset()


def create_openwakeword_engine(settings: AxiomSettings) -> OpenWakeWordEngine:
    """Create the custom wake-word detector from user settings."""
    if settings.wakeword_model_path is None:
        raise WakeWordModelError("No custom Hey Axiom ONNX model path is configured.")
    return OpenWakeWordEngine(
        model_path=settings.wakeword_model_path,
        threshold=settings.wakeword_threshold,
        patience=settings.wakeword_patience,
    )
