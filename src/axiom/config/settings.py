"""Load the small set of user-level runtime settings."""

from __future__ import annotations

import os
import platform
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AxiomSettings:
    """Settings that connect local wake detection to Codex Desktop."""

    codex_voice_shortcut: str | None = None


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
    if not config_path.exists():
        return AxiomSettings()

    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    codex = data.get("codex", {})
    if not isinstance(codex, dict):
        raise ValueError("The [codex] configuration section must be a table.")

    shortcut = codex.get("voice_shortcut")
    if shortcut is not None and (not isinstance(shortcut, str) or not shortcut.strip()):
        raise ValueError("codex.voice_shortcut must be a non-empty string.")

    return AxiomSettings(codex_voice_shortcut=shortcut.strip() if shortcut else None)
