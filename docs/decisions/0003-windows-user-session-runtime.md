# ADR 0003: Run in the Signed-in Windows User Session

- Status: Accepted
- Date: 2026-11-04

## Context

Axiom needs continuous microphone access for local wake-word detection and sends a keyboard shortcut to the signed-in user's ChatGPT Desktop app. Windows Services run in a noninteractive session and do not fit this desktop workflow.

## Decision

- Run Axiom as a regular Python process in the signed-in user's session.
- Start the process at user sign-in through a launcher script and a per-user startup mechanism.
- Use an awaited async frame loop: read microphone input, run local wake-word detection, send the configured Codex Voice shortcut on a match, then resume waiting for the next wake phrase.
- Keep device callbacks and platform-specific audio behavior inside the future audio adapter.
- Do not register automatic startup on the development machine. Enable it only after the target audio and shortcut behavior are ready.

## Consequences

- Axiom can use the user's Windows-selected default microphone input.
- ChatGPT Desktop Voice handles its own conversation audio through the Windows-selected devices.
- The application stops when the user session ends or the process exits.
- No administrator service installation is required.
- The committed PowerShell launcher is a per-user process entry point, not a service installer.
