# Axiom Architecture

- Status: Draft
- Version: 0.1
- Last updated: 2026-11-04

## Product definition

Axiom is a local-first voice companion that helps a person practice spoken English through natural, real-time conversation. It starts with a local wake phrase and uses the audio input and output selected in Windows, while keeping conversation providers and future home capabilities behind replaceable interfaces.

The first project milestone establishes the Python package, the per-user background process model, the device-independent wake/conversation loop, and the boundaries between audio, wake-word, and voice adapters. It does not assume that the SP96 is attached to the development computer.

## Goals

- Use the product name Axiom and the wake phrase `Hey Axiom` consistently.
- Let Windows Sound Settings own audio-device selection.
- Use the system-selected default input and output streams without identifying, listing, or switching hardware devices.
- Keep wake-word detection, audio capture, conversation, speech output, and external integrations as separate components.
- Keep the Codex Desktop integration behind an adapter so the conversation system does not depend on undocumented desktop behavior.
- Keep project files, comments, and user-facing text in English.
- Make missing hardware and unavailable services normal, diagnosable states.

## Non-goals for the first milestone

- Enabling automatic startup before testing on the target machine.
- Enumerating hardware, matching SP96 endpoint names, or changing Windows audio settings.
- Replacing ChatGPT Desktop's own voice experience or reproducing its task context.
- Adding home-control actions, persistent conversation memory, or account integrations.

## Proposed component model

```text
┌──────────────────────┐
│ CLI / local control  │
└──────────┬───────────┘
           │ commands and status
┌──────────▼───────────┐       ┌─────────────────────┐
│ Application runtime  ├──────►│ Configuration       │
└──────────┬───────────┘       └─────────────────────┘
           │
     ┌─────┴───────────┐
     │                 │
┌────▼─────┐      ┌────▼──────────┐
│ Wakeword │      │   Audio I/O   │
│ adapter  │      │ and capture   │
└────┬─────┘      └────┬──────────┘
     └──────────┬───────┘
          ┌─────▼──────────┐
          │ Session manager│
          └─────┬──────────┘
        ┌───────┴─────────────┐
        │                     │
┌───────▼────────┐    ┌───────▼────────────┐
│ Voice provider │    │ External adapters  │
│ interface      │    │ Codex Desktop, etc.│
└───────┬────────┘    └────────────────────┘
        │
┌───────▼────────┐
│ Speech output  │
└────────────────┘
```

### Component responsibilities

| Component | Responsibility | Initial boundary |
| --- | --- | --- |
| CLI and local control | Show status, hand off to Codex Desktop, or launch the resident process | Importing or checking status never opens audio |
| Configuration | Store runtime options and provider preferences | User-level configuration; secrets stay out of the repository |
| Audio I/O contract | Deliver microphone frames and accept output frames | Interface only; backend waits for target-device integration |
| Wake-word adapter | Detect `Hey Axiom` locally | Interface only; engine choice remains open |
| Runtime | Wait for frames, switch between wake listening and conversation, close cleanly | State loop implemented; adapters injected later |
| Voice provider | Supply a real-time spoken conversation | Interface only; provider choice remains open |
| Codex Desktop adapter | Report app readiness and native voice handoff | No undocumented UI injection |

## Audio I/O design

Windows Sound Settings owns microphone and speaker selection. `AudioIO` is an async interface for input frames and output frames. The runtime knows only about PCM frames; the device backend that opens Windows defaults is intentionally deferred until the SP96 is available for integration.

The eventual backend will not enumerate endpoints, match the string `SP96`, provide device-selection controls, or change system audio settings. It will bridge audio callbacks into the async frame iterator without blocking the event loop. Audio will not be saved by default.

The Yealink SP96 is the planned speakerphone for end-to-end validation after it arrives. Its product description lists USB, Bluetooth, and USB-adapter connectivity: [Yealink SP96](https://www.yealink.com/en/product-detail/speakerphone-sp96). Axiom does not depend on the SP96 model name or its endpoint names.

## Windows process and async loop

Run Axiom as a normal process in the signed-in user's session, optionally launched at sign-in through the Windows Startup folder or a scheduled task configured to run only while that user is logged on. Do not use a Windows Service for microphone access or user-facing voice behavior: services run in a noninteractive session and cannot directly interact with the user. See [Microsoft's Interactive Services guidance](https://learn.microsoft.com/en-us/windows/desktop/Services/interactive-services).

The runtime follows this state flow:

```text
STARTING -> WAITING_FOR_WAKEWORD -> CONVERSING -> WAITING_FOR_WAKEWORD
     \____________________________-> STOPPING -> STOPPED
```

`AxiomRuntime` awaits the next audio frame instead of polling continuously. In the waiting state it feeds frames to the local wake-word engine. On a match, it passes the same frame stream, a short pre-roll, and the output contract to the voice session. When the session returns, it resets wake-word state and resumes waiting. Cancellation exits the audio context and closes resources.

The future device backend may receive callbacks on an audio thread. It must hand frames to the async runtime using a thread-safe bridge; it must not call `asyncio.Queue` methods directly from another thread. Python documents `loop.call_soon_threadsafe()` for this boundary: [asyncio multithreading guidance](https://docs.python.org/3/library/asyncio-dev.html).

## Codex Desktop voice integration

ChatGPT Desktop provides voice conversations for Codex tasks. The documented flow starts voice from within a Codex task, and availability can depend on client rollout, account, and workspace. See [ChatGPT Voice](https://developers.openai.com/es-419/docs/features/voice) and [Using voice](https://developers.openai.com/training/walkthroughs/using-voice).

Treat Codex Desktop voice as an external conversation surface. Axiom should not assume it can start, steer, or inspect a desktop voice session through a public API. The first adapter can provide readiness information and a handoff guide; an automated control path requires a documented and supported interface.

Axiom's own real-time conversation provider remains a separate component. This keeps the core English-practice experience independent of Codex Desktop availability and allows future providers without changing audio-device or wake-word code.

## Configuration proposal

Use a user-level TOML configuration, with defaults suitable for first launch. Audio-device selection is intentionally absent because Windows owns it:

```toml
[wakeword]
enabled = false
phrase = "Hey Axiom"

[privacy]
save_audio = false
```

The configuration path and exact schema should be settled when the CLI foundation is implemented. Provider credentials should be loaded from the operating-system environment or a secure local credential store, never committed to the repository.

## Proposed implementation layout

```text
src/axiom/
├── __init__.py
├── __main__.py
├── cli.py
├── config/
├── audio/
│   └── io.py
├── wakeword/
│   └── engine.py
├── voice/
│   └── session.py
├── integrations/
│   └── codex_desktop.py
└── runtime/
    ├── app.py
    └── state.py
```

The public package name and console command are both `axiom`. `axiom run` is the resident entry point. It currently exits with a clear adapter-pending message rather than starting an idle process. Keep import-time behavior side-effect free: importing the package must not open a microphone, start a background process, or contact a voice provider.

## Open design questions

1. Should the first conversational release use ChatGPT Desktop's native voice flow, or should Axiom own the full voice session through a provider API?
2. If Axiom owns the session, which provider, account model, and data-retention behavior are acceptable?
3. Which local wake-word engine and license fit the target distribution?
4. Should Windows be the only supported platform for the first release?
5. Should an active conversation reopen audio after Windows changes a default endpoint, or ask the user to restart the session?
