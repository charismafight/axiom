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

This repository contains the Python package foundation, an async wake-word runtime, an openWakeWord adapter, user settings, and the Windows keyboard shortcut sender. The device-dependent microphone backend and custom `Hey Axiom` ONNX model are not included yet. Axiom does not use a separate AI provider or implement its own TTS.

The intended Windows process is a regular per-user background app launched at sign-in, not a Windows Service. The launcher is [scripts/start_axiom.ps1](scripts/start_axiom.ps1). It is not registered for automatic startup on this development machine, and `axiom run` exits with an adapter-pending message until the microphone backend and custom model are available.

Windows Sound Settings owns device selection; Axiom will not identify or select the SP96. Configure a Voice shortcut in ChatGPT Desktop Settings > Voice and put the same chord in `%APPDATA%\Axiom\config.toml`. Axiom sends that shortcut after offline wake-word detection; ChatGPT Desktop owns the Voice session.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[wakeword]"
axiom status
axiom codex
.\scripts\start_axiom.ps1
```

User-level configuration (`%APPDATA%\Axiom\config.toml`):

```toml
[codex]
voice_shortcut = "CTRL+SHIFT+V"

[wakeword]
model_path = '%APPDATA%\Axiom\models\hey_axiom.onnx'
threshold = 0.5
patience = 2
```

Use the same shortcut configured in ChatGPT Desktop; the example is not a default. The ONNX file must be a custom model for `Hey Axiom`; Axiom does not bundle an upstream pre-trained model. See the [openWakeWord custom model training guide](https://github.com/dscripka/openWakeWord#training-new-models). OpenAI documents that Voice in Work or Codex can use a shortcut configured in Settings: [ChatGPT Work and Codex](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex).

The openWakeWord runtime code is Apache-2.0, while its included pre-trained models have a separate non-commercial license. Axiom loads only the explicitly configured custom model and does not use or include those upstream models. See the [openWakeWord license notes](https://github.com/dscripka/openWakeWord#license).

openWakeWord also requires shared ONNX feature-extractor assets. Axiom does not provision these yet; the follow-up setup step must add only the shared feature assets. Do not run the upstream no-argument `download_models()` helper, which downloads its pre-trained wake-word classifiers as well.

`scripts/start_axiom.ps1` invokes `python -m axiom run`. The resident entry point currently reports that runtime adapters are pending rather than leaving an idle process running.

## Design documents

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
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

The package provides status and Codex Desktop readiness commands. The wake-listen/shortcut-trigger loop and model adapter are independent of hardware; the Windows microphone backend and custom wake-word model remain to be supplied.
