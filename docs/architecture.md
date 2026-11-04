# Axiom Architecture

- Status: Draft
- Version: 0.1
- Last updated: 2026-11-04

## Product definition

Axiom is a local-first voice companion that helps a person practice spoken English through natural, real-time conversation. It starts with a local wake phrase and uses the audio input and output selected in Windows, while keeping conversation providers and future home capabilities behind replaceable interfaces.

The first project milestone establishes the Python package, uses the input and output devices selected as Windows defaults, and defines how Axiom relates to voice in ChatGPT Desktop's Codex tasks. It does not assume that the SP96 is attached to the development computer.

## Goals

- Use the product name Axiom and the wake phrase `Hey Axiom` consistently.
- Let Windows Sound Settings own audio-device selection.
- Open the system-selected default input and output streams without identifying, listing, or switching hardware devices.
- Keep wake-word detection, audio capture, conversation, speech output, and external integrations as separate components.
- Keep the Codex Desktop integration behind an adapter so the conversation system does not depend on undocumented desktop behavior.
- Keep project files, comments, and user-facing text in English.
- Make missing hardware and unavailable services normal, diagnosable states.

## Non-goals for the first milestone

- Shipping a production background service before testing on the target machine.
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
| CLI and local control | Show status and run explicit diagnostics | No background capture by default |
| Configuration | Store runtime options and provider preferences | User-level configuration; secrets stay out of the repository |
| Audio I/O | Open Windows-selected default input and output streams using PortAudio through `sounddevice` | Raw 48 kHz mono PCM; no device inventory, matching, or selection UI |
| Audio capture | Acquire audio frames from the system-selected input | Added after backend and hardware validation |
| Wake-word adapter | Detect `Hey Axiom` locally | Engine choice remains open |
| Session manager | Coordinate listening, conversation, interruption, and shutdown | Must own a clear state machine |
| Voice provider | Supply real-time speech conversation | Replaceable provider interface |
| Codex Desktop adapter | Describe or invoke supported Codex voice entry points | No undocumented UI injection |
| Speech output | Play assistant audio through the system-selected output | Added after end-to-end device validation |

## Audio I/O design

Windows Sound Settings owns microphone and speaker selection. Axiom opens the system-selected default input and output streams through PortAudio via `sounddevice`, passing `device=None`. It does not enumerate endpoints, match the string `SP96`, provide device-selection controls, or change system audio settings.

The initial stream format is 48 kHz, mono, signed 16-bit PCM. Keep input and output stream status separate so Axiom can report which default stream failed to open. On failure, direct the user to Windows Sound Settings to choose or repair the default device. Validate that PortAudio follows Windows defaults and that the stream format works with the target device after the SP96 arrives.

The Yealink SP96 is the planned speakerphone for end-to-end validation after it arrives. Its product description lists USB, Bluetooth, and USB-adapter connectivity: [Yealink SP96](https://www.yealink.com/en/product-detail/speakerphone-sp96). Axiom does not depend on the SP96 model name or its endpoint names.

Do not save microphone audio by default. Opening an input stream should only occur when the user starts an audio session or enables the wake-word runtime. Any future capture diagnostic should be explicit, bounded in duration, and should discard audio unless the user explicitly enables recording.

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
├── cli/
├── config/
├── audio/
│   └── io.py
├── wakeword/
├── voice/
├── integrations/
│   └── codex_desktop/
└── runtime/
```

The public package name and console command are both `axiom`. Keep import-time behavior side-effect free: importing the package must not open a microphone, start a service, or contact a voice provider.

## Open design questions

1. Should the first conversational release use ChatGPT Desktop's native voice flow, or should Axiom own the full voice session through a provider API?
2. If Axiom owns the session, which provider, account model, and data-retention behavior are acceptable?
3. Which local wake-word engine and license fit the target distribution?
4. Should Windows be the only supported platform for the first release?
5. Should an active session reopen its streams automatically when Windows changes a default endpoint, or stop and ask the user to restart it?
