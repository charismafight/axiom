"""Command-line entry point for Axiom."""

from __future__ import annotations

import argparse
import asyncio
import sys

from axiom import __version__
from axiom.config import get_config_path, load_settings
from axiom.integrations.codex_desktop import get_desktop_status
from axiom.integrations.windows_shortcut import InvalidShortcut, KeyboardShortcut
from axiom.runtime import RuntimeAdaptersPending, build_runtime


def _show_status() -> int:
    print(f"Axiom {__version__}")
    print("Project stage: foundation")
    print("Microphone: Windows default input; stream is not open")
    try:
        settings = load_settings()
    except (OSError, ValueError) as error:
        print(f"User configuration: invalid ({error})")
        return 1
    if settings.wakeword_model_path and settings.wakeword_model_path.is_file():
        print(
            "Wake phrase: Hey Axiom (custom ONNX model: "
            f"{settings.wakeword_model_path})"
        )
    else:
        print(
            "Wake phrase: Hey Axiom (custom ONNX model missing: "
            f"{settings.wakeword_model_path})"
        )
    if settings.codex_voice_shortcut:
        try:
            shortcut = KeyboardShortcut.parse(settings.codex_voice_shortcut)
        except InvalidShortcut as error:
            print(f"Codex voice shortcut: invalid ({error})")
            return 1
        print(f"Codex voice shortcut: {shortcut.display}")
    else:
        print(f"Codex voice shortcut: not configured ({get_config_path()})")
    return 0


def _show_codex_status() -> int:
    status = get_desktop_status()
    try:
        settings = load_settings()
    except (OSError, ValueError) as error:
        print(f"Axiom configuration: invalid ({error})")
        return 1

    if status.running is True:
        print("ChatGPT Desktop: running")
    elif status.running is False:
        print("ChatGPT Desktop: not running")
    else:
        print("ChatGPT Desktop: status unavailable")
        if status.detail:
            print(f"Details: {status.detail}")

    if settings.codex_voice_shortcut:
        try:
            shortcut = KeyboardShortcut.parse(settings.codex_voice_shortcut)
        except InvalidShortcut as error:
            print(f"Codex voice shortcut: invalid ({error})")
            return 1
        print(f"Codex voice shortcut: {shortcut.display}")
    else:
        print(f"Codex voice shortcut: not configured ({get_config_path()})")
    print("Set the same shortcut in ChatGPT Desktop Settings > Voice.")
    print("Open a Codex task before triggering Voice with the wake phrase.")
    print("Codex handles conversation capture and speech output.")
    return 0 if status.running is not None else 1


def _run_runtime() -> int:
    try:
        runtime = build_runtime()
    except RuntimeAdaptersPending as error:
        print(str(error), file=sys.stderr)
        return 2

    try:
        asyncio.run(runtime.run())
    except KeyboardInterrupt:
        return 0
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axiom",
        description="Axiom, your AI conversation companion.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Axiom {__version__}",
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("status", help="Show Axiom runtime status.")
    commands.add_parser("codex", help="Show Codex Desktop Voice trigger readiness.")
    commands.add_parser("run", help="Run Axiom as a resident user-session process.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "codex":
        return _show_codex_status()
    if args.command == "run":
        return _run_runtime()
    return _show_status()
