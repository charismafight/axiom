# Axiom Roadmap

**Status:** Draft

## Stage 0: Product and integration design (complete)

- Confirm the product identity, first-use scenario, and privacy defaults.
- Define the offline wake-word to ChatGPT Desktop Voice shortcut flow.
- Document Windows device and process assumptions.

**Exit criteria:** The local wake-to-shortcut behavior and system boundaries are documented and accepted.

## Stage 1: Python package foundation (complete)

- Create the `axiom` package and console entry point.
- Add user-level TOML configuration for the Codex Voice shortcut and wake-word model.
- Keep imports side-effect free and audio, wake-word, and shortcut adapters replaceable.
- Add the openWakeWord adapter with an explicit custom ONNX model path.
- Add Codex Desktop process status and a Windows keyboard shortcut sender.
- Add the async wake-word runtime and the per-user Windows launcher script.

**Exit criteria:** The device-independent wake/shortcut flow and wake-word adapter are defined. `axiom run` reports missing configuration or model resources without opening audio or keeping an empty process alive.

## Stage 2: Windows microphone and offline wake word (implementation complete; SP96 validation pending)

- [x] Publish an initial custom `Hey Axiom` ONNX classifier with its license and training-data provenance.
- [x] Verify `axiom prepare-wakeword` provisions only the shared ONNX feature assets.
- [x] Verify CPU classifier initialization and synthetic-silence inference with the provisioned shared feature assets.
- [x] Implement microphone capture from the Windows-selected default input.
- [x] Bridge audio callbacks into the async frame iterator safely.
- [x] Feed frames to the local wake-word detector without saving them.
- [ ] Validate wake detection and microphone error recovery after the SP96 arrives and is selected in Windows.

**Exit criteria:** On the target machine, Axiom detects `Hey Axiom` locally and offline using the Windows default microphone, without a device inventory or selection flow.

## Stage 3: ChatGPT Desktop Voice shortcut (implementation complete; target validation pending)

- [ ] Configure the same keyboard chord in ChatGPT Desktop Settings > Voice and Axiom's TOML settings on the target machine.
- [x] Report ChatGPT Desktop process state and missing or invalid shortcut configuration through the CLI.
- [x] Send the configured shortcut after the wake-word engine reports a match.
- [ ] Confirm the shortcut triggers Voice as expected on the target machine.

**Exit criteria:** The runtime sends the configured chord after a wake-word event, and the CLI reports missing app or shortcut configuration.

## Stage 4: Windows sign-in and long-running behavior

- Validate the resident process under the signed-in Windows user session.
- Perform final end-to-end wake-word and shortcut checks on the target machine, including ChatGPT Desktop foreground/background behavior and duplicate detections.
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
