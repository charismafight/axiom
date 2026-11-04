# ADR 0002: Windows Owns Audio Device Selection

- Status: Accepted
- Date: 2026-11-04

## Context

The user configures microphones and speakers in Windows. Axiom does not need to recognize the Yealink SP96 by name or reproduce the operating system's device-selection controls.

## Decision

- Windows Sound Settings is the sole owner of microphone and speaker selection.
- Axiom opens the system-selected default input and output streams.
- Axiom does not enumerate devices for product selection, match SP96 names, or change Windows audio settings.
- Axiom reports input and output stream failures separately and points the user to Windows Sound Settings.
- The SP96 is used for end-to-end validation after it arrives, not as a runtime identity requirement.

## Consequences

- The product has no device picker or device-name configuration.
- Audio backend selection must be checked to ensure it follows Windows defaults.
- Axiom remains compatible with other microphones and speakers selected in Windows.
- Tests on the target machine still need to cover default-device changes, disconnection, and reconnection.
