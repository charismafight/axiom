"""Command-line entry point for Axiom."""

from __future__ import annotations

import argparse

from axiom import __version__
from axiom.integrations.codex_desktop import get_desktop_status


def _show_status() -> int:
    print(f"Axiom {__version__}")
    print("Project stage: foundation")
    print("Audio I/O: Windows default input and output; streams are not open")
    print("Wake phrase: Hey Axiom (not active)")
    return 0


def _show_codex_status() -> int:
    status = get_desktop_status()

    if status.running is True:
        print("ChatGPT Desktop: running")
    elif status.running is False:
        print("ChatGPT Desktop: not running")
    else:
        print("ChatGPT Desktop: status unavailable")
        if status.detail:
            print(f"Details: {status.detail}")

    print("Codex voice: start or join a voice chat inside a Codex task in ChatGPT Desktop.")
    print("Availability can depend on client rollout, account, and workspace settings.")
    print("Axiom does not start or control the desktop voice session.")
    return 0 if status.running is not None else 1


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
    commands.add_parser("codex", help="Show Codex Desktop voice handoff status.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "codex":
        return _show_codex_status()
    return _show_status()
