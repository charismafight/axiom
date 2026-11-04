# ADR 0003: Run in the Signed-in Windows User Session

- Status: Accepted
- Date: 2026-11-04

## Context

Axiom needs continuous microphone access for local wake-word detection and may show user-facing status or settings. The application is intended for one signed-in desktop user, not for machine-wide unattended work.

Windows Services run in a noninteractive session and cannot directly interact with the user. A service would add privilege and session-management complexity without helping Axiom's core audio workflow.

## Decision

- Run Axiom as a regular Python process in the signed-in user's session.
- Start the process at user sign-in through a launcher script and a per-user startup mechanism.
- Use an awaited async frame loop: wait for the next audio frame, run local wake-word detection, enter the conversation state on a match, and return to wake-word listening when the voice session ends.
- Keep device callbacks and platform-specific audio behavior inside the future audio adapter.
- Do not register automatic startup on the development machine. Enable it only after the target audio and provider adapters are ready.

## Consequences

- Axiom can use the user's Windows-selected default audio input and output.
- The application stops when the user session ends or the process exits.
- No administrator service installation is required.
- The committed PowerShell launcher is a per-user process entry point, not a service installer.
