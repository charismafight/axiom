# Axiom Roadmap

**Status:** Draft

## Stage 0: Product and integration design

- Confirm the product identity, first-use scenario, and privacy defaults.
- Define the offline wake-word to ChatGPT Desktop Voice shortcut flow.
- Document Windows device and process assumptions.

**Exit criteria:** Axiom detects a local wake phrase and triggers the Voice shortcut configured for a Codex task. ChatGPT Desktop owns the conversation audio and AI interaction.

## Stage 1: Python package foundation

- Create the `axiom` package and console entry point.
- Add user-level TOML configuration for the Codex Voice shortcut.
- Keep imports side-effect free and audio, wake-word, and shortcut adapters replaceable.
- Add Codex Desktop process status and a Windows keyboard shortcut sender.
- Add the async wake-word runtime and the per-user Windows launcher script.

**Exit criteria:** The device-independent wake/shortcut flow is defined. `axiom run` reports missing microphone and wake-word adapters without opening audio or keeping an empty process alive.

## Stage 2: Windows microphone and offline wake word

- Select an offline wake-word engine and confirm its license and operating requirements.
- Implement microphone capture from the Windows-selected default input.
- Bridge audio callbacks into the async frame iterator safely.
- Feed frames to the local wake-word detector without saving them.
- Validate wake detection and microphone error recovery after the SP96 arrives and is selected in Windows.

**Exit criteria:** On the target machine, Axiom detects `Hey Axiom` locally and offline using the Windows default microphone, without a device inventory or selection flow.

## Stage 3: ChatGPT Desktop Voice shortcut

- Configure the same keyboard chord in ChatGPT Desktop Settings > Voice and Axiom's TOML settings.
- Verify the shortcut starts Voice in an open Codex task.
- Check whether the shortcut works while ChatGPT Desktop is in the background.
- Check duplicate detection behavior while Voice is active.
- Handle unavailable app, missing shortcut, and invalid shortcut configurations clearly.

**Exit criteria:** A local wake phrase reliably triggers the configured Codex Voice shortcut on the target installation.

## Stage 4: Windows sign-in and long-running behavior

- Validate the resident process under the signed-in Windows user session.
- Add optional per-user startup registration only after target hardware and shortcut validation.
- Confirm graceful stop, restart, logging, and recovery from microphone disconnection.

**Exit criteria:** Axiom starts and stops predictably in the intended user's session and recovers from expected device failures.

## Stage 5: Future capabilities

- Add capabilities behind explicit permission boundaries.
- Add durable preferences only after choosing a storage and deletion model.
- Revisit a broader home-assistant role when the first use case is stable.

**Exit criteria:** New capabilities do not couple local wake detection to a single desktop application.

## Release principle

Do not label the application production-ready until wake detection, shortcut behavior, permissions, error handling, and long-running reliability have been checked on the actual target machine and hardware.
