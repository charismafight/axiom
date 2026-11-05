# Axiom

**Your AI Conversation Companion**<br>
Think. Speak. Explore.

Axiom is a Windows resident voice companion for spoken English practice. It listens for `Hey Axiom` with an offline wake-word detector, then sends the keyboard shortcut configured for Voice in ChatGPT Desktop. ChatGPT Desktop handles the conversation, microphone capture during the conversation, and speech output.

## Product identity

- Product name: Axiom
- Spoken name: Axiom (`/ˈæk.si.əm/`)
- Wake phrase: `Hey Axiom`
- Git repository and Python package: `axiom`
- Intended project directory: `C:\Projects\Axiom`
- License: MIT ([license text](LICENSE))

Project files, source code, comments, and user-facing strings are written in English.

## Current stage

This repository contains the Python package foundation, an async wake-word runtime, a Windows-default microphone adapter, an openWakeWord adapter, user settings, the published custom `Hey Axiom` ONNX model, and the Windows keyboard shortcut sender. Target-device reliability and wake-word quality still need validation with the SP96. Axiom does not use a separate AI provider or implement its own TTS.

The intended Windows process is a regular per-user background app launched at sign-in, not a Windows Service. The launcher is [scripts/start_axiom.ps1](scripts/start_axiom.ps1). It is not registered for automatic startup on this development machine. `axiom run` opens the Windows default input after the model, feature assets, and Voice shortcut are configured.

Windows Sound Settings owns device selection; Axiom will not identify or select the SP96. Configure a Voice shortcut in ChatGPT Desktop Settings > Voice and put the same chord in `%APPDATA%\Axiom\config.toml`. Axiom sends that shortcut after offline wake-word detection; ChatGPT Desktop owns the Voice session.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[audio,wakeword]"
$AxiomModelDirectory = Join-Path $env:APPDATA "Axiom\models"
New-Item -ItemType Directory -Force -Path $AxiomModelDirectory | Out-Null
Copy-Item .\models\hey_axiom.onnx (Join-Path $AxiomModelDirectory "hey_axiom.onnx") -Force
axiom status
axiom codex
axiom prepare-wakeword
axiom test
.\scripts\start_axiom.ps1
```

Run `axiom test` to capture five seconds from the Windows default input. It reports the negotiated capture rate and channel count plus peak and RMS levels, then discards the audio. Speak normally while it runs; use `axiom test --duration 10` for a longer check.

User-level configuration (`%APPDATA%\Axiom\config.toml`):

```toml
[codex]
voice_shortcut = "CTRL+SHIFT+V"

[wakeword]
model_path = '%APPDATA%\Axiom\models\hey_axiom.onnx'
threshold = 0.5
patience = 2
```

Use the same shortcut configured in ChatGPT Desktop; the example is not a default. Axiom includes its own custom `Hey Axiom` model and does not use openWakeWord pre-trained wake-word classifiers. See the [openWakeWord custom model training guide](https://github.com/dscripka/openWakeWord#training-new-models). OpenAI documents that Voice in Work or Codex can use a shortcut configured in Settings: [ChatGPT Work and Codex](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex).

The openWakeWord runtime code is Apache-2.0. The published Axiom model has a separate CC BY-NC-SA 4.0 license; upstream pre-trained classifiers are not used. See the [openWakeWord license notes](https://github.com/dscripka/openWakeWord#license) and the [Axiom custom model guide](docs/wakeword-model.md).

Run `axiom prepare-wakeword` once while online to download and validate the two shared ONNX feature-extractor assets. They are stored next to the configured classifier under `openwakeword`. The command downloads only these shared assets; it does not fetch upstream pre-trained wake-word classifiers. Wake detection itself performs local inference and does not need a network connection.

`scripts/start_axiom.ps1` invokes `python -m axiom run`. Before opening the microphone, `axiom run` validates the model, shared feature assets, and configured Voice shortcut. If a prerequisite is missing, it exits with an actionable message instead of leaving an idle process running. Press `Ctrl+C` to stop it.

## Design documents

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Custom wake-word model](docs/wakeword-model.md)
- [Codex Desktop voice shortcut](docs/decisions/0001-codex-desktop-voice-boundary.md)
- [Windows process model](docs/decisions/0003-windows-user-session-runtime.md)
- [Offline wake-word engine](docs/decisions/0004-offline-wakeword-engine.md)

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
```

The CLI provides status, Codex Desktop readiness, wake-word asset preparation, microphone signal testing, and the resident `run` command. The wake-listen/shortcut-trigger loop is connected to the Windows default input; target-hardware and long-running reliability checks remain.
