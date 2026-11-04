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

This repository contains the Python package foundation, an async runtime state loop, adapter contracts, and product design. The device-dependent audio backend, wake-word engine, and voice provider are intentionally not implemented yet.

The intended Windows process is a regular per-user background app launched at sign-in, not a Windows Service. The launcher is [scripts/start_axiom.ps1](scripts/start_axiom.ps1). It is not registered for automatic startup on this development machine, and `axiom run` exits with an adapter-pending message until the device-dependent pieces are connected.

Windows Sound Settings owns device selection; Axiom will not identify or select the SP96. The Codex CLI reports desktop readiness and explains the native voice handoff; it does not start or steer a voice session.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
axiom status
axiom codex
.\scripts\start_axiom.ps1
```

`scripts/start_axiom.ps1` invokes `python -m axiom run`. The resident entry point currently reports that runtime adapters are pending rather than leaving an idle process running.

## Design documents

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Codex Desktop voice boundary](docs/decisions/0001-codex-desktop-voice-boundary.md)
- [Windows process model](docs/decisions/0003-windows-user-session-runtime.md)

## Project layout

```text
axiom/
├── docs/
│   └── decisions/
├── scripts/
│   └── start_axiom.ps1
└── src/
    └── axiom/
        ├── audio/
        ├── config/
        ├── integrations/
        ├── runtime/
        ├── wakeword/
        └── voice/
```

The package provides status and Codex Desktop handoff commands. The wake-listen/conversation state loop is independent of hardware; concrete audio, wake-word, and voice adapters remain planned work.
