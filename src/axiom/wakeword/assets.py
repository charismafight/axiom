"""Provision the shared ONNX feature assets used by openWakeWord."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


class WakeWordAssetsError(RuntimeError):
    """Raised when wake-word feature assets cannot be prepared or validated."""


@dataclass(frozen=True, slots=True)
class FeatureAssetResult:
    """The result for one shared feature asset."""

    path: Path
    downloaded: bool


_FEATURE_ASSETS = (
    (
        "melspectrogram.onnx",
        "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/"
        "melspectrogram.onnx",
        "input",
    ),
    (
        "embedding_model.onnx",
        "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/"
        "embedding_model.onnx",
        "input_1",
    ),
)
_DOWNLOAD_TIMEOUT_SECONDS = 60
_DOWNLOAD_CHUNK_BYTES = 1024 * 1024


def get_feature_assets_dir(model_path: Path) -> Path:
    """Return the shared feature-asset directory for a wake-word classifier."""
    return model_path.parent / "openwakeword"


def prepare_feature_assets(model_path: Path) -> tuple[FeatureAssetResult, ...]:
    """Download and validate only openWakeWord's shared ONNX feature assets."""
    try:
        import onnxruntime as ort
    except ImportError as error:
        raise WakeWordAssetsError(
            "ONNX Runtime is missing. Install Axiom with its wakeword extra first."
        ) from error

    target_directory = get_feature_assets_dir(model_path)
    try:
        target_directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise WakeWordAssetsError(
            f"Could not create the wake-word asset directory {target_directory}: {error}"
        ) from error

    results: list[FeatureAssetResult] = []
    for filename, url, expected_input in _FEATURE_ASSETS:
        target = target_directory / filename
        if target.is_file() and _is_valid_onnx(target, expected_input, ort):
            results.append(FeatureAssetResult(path=target, downloaded=False))
            continue

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{filename}.",
                suffix=".part",
                dir=target_directory,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                request = Request(url, headers={"User-Agent": "Axiom/0.1"})
                with urlopen(request, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
                    while chunk := response.read(_DOWNLOAD_CHUNK_BYTES):
                        temporary_file.write(chunk)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            if not _is_valid_onnx(temporary_path, expected_input, ort):
                raise WakeWordAssetsError(
                    f"Downloaded asset {filename} is not a compatible ONNX model."
                )

            os.replace(temporary_path, target)
            temporary_path = None
            results.append(FeatureAssetResult(path=target, downloaded=True))
        except WakeWordAssetsError:
            raise
        except OSError as error:
            raise WakeWordAssetsError(
                f"Could not download {filename} from its pinned openWakeWord release: {error}"
            ) from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    return tuple(results)


def _is_valid_onnx(path: Path, expected_input: str, ort: Any) -> bool:
    """Check that ONNX Runtime can load the asset and find its expected input."""
    try:
        session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        return any(item.name == expected_input for item in session.get_inputs())
    except Exception:
        return False
