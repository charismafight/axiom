"""Readiness information for the native ChatGPT Desktop Codex voice flow."""

from __future__ import annotations

import csv
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DesktopStatus:
    running: bool | None
    detail: str | None = None


class VoiceShortcut(Protocol):
    """Trigger the user-configured ChatGPT Desktop voice shortcut."""

    def trigger(self) -> None:
        """Send the configured shortcut through the system input stream."""
        ...


def _windows_status() -> DesktopStatus:
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return DesktopStatus(running=None, detail=str(error))

    if result.returncode != 0:
        return DesktopStatus(running=None, detail=result.stderr.strip() or "tasklist failed")

    process_names = {
        row[0].casefold()
        for row in csv.reader(result.stdout.splitlines())
        if row
    }
    return DesktopStatus(running="chatgpt.exe" in process_names)


def _posix_status() -> DesktopStatus:
    pgrep = shutil.which("pgrep")
    if pgrep is None:
        return DesktopStatus(running=None, detail="pgrep is not available")

    try:
        result = subprocess.run(
            [pgrep, "-x", "ChatGPT"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return DesktopStatus(running=None, detail=str(error))

    if result.returncode == 0:
        return DesktopStatus(running=True)
    if result.returncode == 1:
        return DesktopStatus(running=False)
    return DesktopStatus(running=None, detail=result.stderr.strip() or "pgrep failed")


def get_desktop_status() -> DesktopStatus:
    """Check whether the ChatGPT Desktop process appears to be running."""
    system = platform.system()
    if system == "Windows":
        return _windows_status()
    if system in {"Darwin", "Linux"}:
        return _posix_status()
    return DesktopStatus(running=None, detail=f"Unsupported operating system: {system}")
