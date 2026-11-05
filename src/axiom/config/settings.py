"""Load the small set of user-level runtime settings."""

from __future__ import annotations

import os
import platform
import tomllib
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CODEX_VOICE_SHORTCUT = "CTRL+SHIFT+ALT+S"


@dataclass(frozen=True, slots=True)
class AxiomSettings:
    """Settings for offline wake detection and Codex Desktop Voice."""

    codex_voice_shortcut: str | None = DEFAULT_CODEX_VOICE_SHORTCUT
    wakeword_model_path: Path | None = None
    wakeword_threshold: float = 0.5
    wakeword_patience: int = 2


def get_config_path() -> Path:
    """Return the per-user TOML configuration path."""
    if platform.system() == "Windows":
        app_data = os.environ.get("APPDATA")
        root = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return root / "Axiom" / "config.toml"

    config_home = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_home) if config_home else Path.home() / ".config"
    return root / "axiom" / "config.toml"


def load_settings(path: Path | None = None) -> AxiomSettings:
    """Load settings, returning defaults when no user config exists."""
    config_path = path or get_config_path()
    if config_path.exists():
        with config_path.open("rb") as config_file:
            data = tomllib.load(config_file)
    else:
        data = {}

    codex = data.get("codex", {})
    if not isinstance(codex, dict):
        raise ValueError("The [codex] configuration section must be a table.")

    shortcut = codex.get("voice_shortcut", DEFAULT_CODEX_VOICE_SHORTCUT)
    if shortcut is not None and (not isinstance(shortcut, str) or not shortcut.strip()):
        raise ValueError("codex.voice_shortcut must be a non-empty string.")

    wakeword = data.get("wakeword", {})
    if not isinstance(wakeword, dict):
        raise ValueError("The [wakeword] configuration section must be a table.")

    model_path_value = wakeword.get("model_path")
    if model_path_value is not None and (
        not isinstance(model_path_value, str) or not model_path_value.strip()
    ):
        raise ValueError("wakeword.model_path must be a non-empty string.")
    if model_path_value:
        expanded_path = os.path.expandvars(os.path.expanduser(model_path_value.strip()))
        model_path = Path(expanded_path)
        if not model_path.is_absolute():
            model_path = config_path.parent / model_path
    else:
        model_path = config_path.parent / "models" / "hey_axiom.onnx"

    threshold = wakeword.get("threshold", 0.5)
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0.0 <= threshold <= 1.0
    ):
        raise ValueError("wakeword.threshold must be a number between 0 and 1.")

    patience = wakeword.get("patience", 2)
    if isinstance(patience, bool) or not isinstance(patience, int) or patience < 1:
        raise ValueError("wakeword.patience must be a positive integer.")

    return AxiomSettings(
        codex_voice_shortcut=shortcut.strip() if shortcut else None,
        wakeword_model_path=model_path,
        wakeword_threshold=float(threshold),
        wakeword_patience=patience,
    )
