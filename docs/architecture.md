# Axiom Architecture

- Status: Draft
- Version: 0.2
- Last updated: 2026-11-04

## Product definition

Axiom is a Windows resident program for spoken English practice. It listens for the wake phrase `Hey Axiom` using a local, offline detector. When detected, it sends the keyboard shortcut configured for Voice in ChatGPT Desktop. ChatGPT Desktop owns the conversation, microphone capture during the conversation, and speech output.

Axiom does not select an AI service, implement its own speech recognition or speech synthesis, or manage speaker devices. The first implementation milestone establishes the Python process, settings, wake-word runtime contract, and shortcut trigger before hardware-specific integration.

## Goals

- Keep wake-word detection local and offline.
- Use the shortcut the user configured in ChatGPT Desktop Settings > Voice.
- Leave conversation capture, AI responses, and speech output to ChatGPT Desktop.
- Let Windows Sound Settings own microphone and speaker selection.
- Keep startup and runtime behavior in the signed-in Windows user session.
- Keep project files, comments, and user-facing text in English.
- Keep imports side-effect free; importing Axiom must not open the microphone or send keyboard input.

## Non-goals for the first milestone

- Building an Axiom-owned AI conversation or TTS service.
- Enumerating hardware, matching the SP96 endpoint name, or changing Windows audio settings.
- Installing Axiom as a Windows Service.
- Controlling Codex conversations through undocumented APIs or reading the desktop UI.
- Registering automatic startup on the development machine before target-machine validation.

## Runtime flow

```text
Windows user sign-in
          │
          ▼
  Axiom resident process
          │
          ├── Windows default microphone ──► offline wake-word detector
          │                                      │
          │                                  Hey Axiom
          │                                      │
          └── configured keyboard shortcut ◄────┘
                         │
                         ▼
               ChatGPT Desktop Voice
                 in a Codex task
                         │
              capture, AI, speech output
```

The async runtime waits for microphone frames instead of polling. Each frame is passed to the local wake-word engine. On a match, Axiom sends one configured shortcut and resets the detector. The conversation then belongs to ChatGPT Desktop; Axiom does not stream audio to it or manage the Voice session.

## Component responsibilities

| Component | Responsibility | Initial boundary |
| --- | --- | --- |
| CLI | Show local status and Codex Desktop readiness | Never opens audio or sends a shortcut during status checks |
| Configuration | Read the user-level shortcut, wake-word model, threshold, and patience settings | No AI credentials or device names |
| Audio input | Yield microphone frames from the Windows default input | Interface only until microphone integration |
| Wake-word engine | Detect `Hey Axiom` locally and offline | openWakeWord adapter accepts an explicit custom ONNX model; no built-in pretrained model is selected |
| Runtime | Wait for frames and trigger the shortcut on a wake match | Async state loop is implemented |
| Codex Desktop integration | Send the configured keyboard chord and report app readiness | Uses Win32 `SendInput`; does not inspect or manipulate desktop UI |
| ChatGPT Desktop | Handle conversation capture, AI responses, and speech output | User-configured Voice shortcut in a Codex task |

## Audio input

The eventual audio backend opens only the Windows-selected default microphone input and yields mono, signed 16-bit little-endian PCM frames at 16 kHz. Axiom does not enumerate devices, match `SP96`, provide a device picker, or change Windows audio settings. Audio is consumed in memory for local wake-word detection and is not saved by default.

ChatGPT Desktop independently uses the microphone and speaker selected by Windows for its Voice session. Axiom has no output audio interface. The Yealink SP96 is planned for end-to-end validation after it arrives, but Axiom does not depend on its name or model.

The future backend must bridge audio callbacks into the async frame iterator without blocking the event loop. Python documents `loop.call_soon_threadsafe()` for crossing into an asyncio event loop from another thread: [asyncio multithreading guidance](https://docs.python.org/3/library/asyncio-dev.html).

## Codex Desktop shortcut

Open ChatGPT Desktop, switch to Codex, and open or create a Codex task. In ChatGPT Desktop Settings > Voice, configure a keyboard shortcut. Put the same chord in Axiom's user configuration. The OpenAI help article confirms Voice in Work or Codex can be started with a shortcut configured in Settings: [ChatGPT Work and Codex](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex).

The configuration key is `codex.voice_shortcut`, for example:

```toml
[codex]
voice_shortcut = "CTRL+SHIFT+V"
```

The example is illustrative; it is not a default. Axiom sends the key chord using the Windows keyboard input API. Axiom does not bring ChatGPT Desktop to the foreground, identify the active task, or detect whether Voice is already active. The user will check shortcut behavior with ChatGPT Desktop foregrounded and in the background during final end-to-end validation after the product is assembled.

ChatGPT Desktop must be running with a Codex task ready. Axiom's status command can report process state and shortcut configuration, but does not change either one. Availability of Voice may depend on account, workspace, and app rollout.

## Configuration

The optional user-level TOML file is located at `%APPDATA%\Axiom\config.toml` on Windows. Axiom does not create it automatically. Use the exact shortcut saved in ChatGPT Desktop Settings > Voice and provide a custom ONNX model trained for `Hey Axiom`:

```toml
[codex]
voice_shortcut = "CTRL+SHIFT+V"

[wakeword]
model_path = '%APPDATA%\Axiom\models\hey_axiom.onnx'
threshold = 0.5
patience = 2
```

The default model path is `%APPDATA%\Axiom\models\hey_axiom.onnx`. Axiom's adapter loads only that explicit model file. It does not load openWakeWord's built-in pretrained wake-word models; those model artifacts have a separate CC BY-NC-SA license even though the runtime code is Apache-2.0. See the [openWakeWord license notes](https://github.com/dscripka/openWakeWord#license). The user must provide a custom model and check the rights that apply to its training data and output.

The openWakeWord runtime also requires shared ONNX feature-extractor assets. Axiom does not provision them yet. The eventual setup flow must install only those shared assets and must not invoke the upstream no-argument `download_models()` helper, which also downloads the separately licensed pre-trained wake-word classifiers.

Supported shortcut key names currently include letters, digits, `F1` through `F24`, and common navigation keys. Supported modifiers are `CTRL`, `ALT`, `SHIFT`, and `WIN`. No shortcut is assumed when the setting is absent. Wake-word `threshold` must be between 0 and 1; `patience` is the number of consecutive 80 ms frames required above the threshold.

## Windows process model

Run Axiom as a normal process in the signed-in user's session, optionally launched at sign-in through the Windows Startup folder or a scheduled task configured to run only while that user is logged on. Do not use a Windows Service: services run in a noninteractive session and do not fit this user-facing desktop workflow. See [Microsoft's Interactive Services guidance](https://learn.microsoft.com/en-us/windows/desktop/Services/interactive-services).

The process lifetime is independent of an individual Codex Voice session. The runtime stays ready for another wake phrase after sending a shortcut. It cannot observe the external Voice session's active/inactive state, so duplicate triggering behavior must be checked against the configured ChatGPT Desktop shortcut on the target installation.

## Proposed implementation layout

```text
src/axiom/
├── cli.py
├── config/
│   └── settings.py
├── audio/
│   └── io.py
├── wakeword/
│   ├── engine.py
│   └── openwakeword_engine.py
├── integrations/
│   ├── codex_desktop.py
│   └── windows_shortcut.py
└── runtime/
    ├── app.py
    └── state.py
```

`axiom run` is the resident entry point. It currently exits with a clear adapter-pending message instead of opening an empty or unavailable audio stream. Keep all import-time behavior side-effect free.

## Open implementation details

1. Generate or obtain a custom `Hey Axiom` ONNX model and verify its license and detection quality.
2. Integrate the Windows default microphone backend after the SP96 arrives.
3. Confirm the app rollout, account, and workspace provide Voice in Codex.
