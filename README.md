# Axiom

**Your AI Conversation Companion**<br>
Think. Speak. Explore.

Axiom is a local-first, always-available voice companion for spoken English practice. Its initial design uses a local wake phrase and a real-time AI conversation, with room to grow into a broader home assistant.

## Product identity

- Product name: Axiom
- Spoken name: Axiom (`/ˈæk.si.əm/`)
- Wake phrase: `Hey Axiom`
- Git repository and Python package: `axiom`
- Intended project directory: `C:\Projects\Axiom`
- License: MIT ([license text](LICENSE))

Project files, source code, comments, and user-facing strings are written in English.

## Current stage

This repository contains the initial Python package foundation, default audio stream adapter, and product design. The next implementation milestones are:

1. Connect default audio streams to the session runtime.
2. End-to-end validation with the SP96 after it arrives.
3. A clearly bounded integration with voice in ChatGPT Desktop's Codex tasks.

Windows Sound Settings owns device selection; Axiom will not identify or select the SP96. The Codex CLI reports desktop readiness and explains the native voice handoff; it does not start or steer a voice session.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
axiom status
axiom codex
```

## Design documents

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Codex Desktop voice boundary](docs/decisions/0001-codex-desktop-voice-boundary.md)

## Proposed project layout

```text
axiom/
├── docs/
│   └── decisions/
└── src/
    └── axiom/
        ├── audio/
        ├── config/
        ├── integrations/
        ├── runtime/
        ├── wakeword/
        └── voice/
```

The package currently provides status and Codex Desktop handoff commands, plus a raw audio stream adapter that is not started by the CLI. Wake-word detection and real-time conversation are planned work.
