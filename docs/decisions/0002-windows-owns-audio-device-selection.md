# ADR 0002: Windows Owns Audio Device Selection

- Status: Accepted
- Date: 2026-11-04

## Context

The user configures microphones and speakers in Windows. Axiom only needs microphone input to detect the local wake phrase; ChatGPT Desktop owns audio during its Voice session.

## Decision

- Windows Sound Settings is the sole owner of microphone and speaker selection.
- Axiom opens the system-selected default microphone input for offline wake-word detection.
- Axiom has no speaker output stream and does not enumerate devices, match SP96 names, or change Windows audio settings.
- ChatGPT Desktop uses the Windows-selected audio devices for its Voice interaction.
- Audio used by Axiom's wake-word detector is not saved by default.

## Consequences

- The product has no device picker or device-name configuration.
- The future audio backend must use Windows' default input and handle stream failure and reconnect.
- The SP96 is used for end-to-end validation after it arrives, not as a runtime identity requirement.
