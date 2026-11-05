# ADR 0001: Codex Desktop Voice Boundary

- Status: Accepted
- Date: 2026-11-04

## Context

Axiom's first use case is spoken English practice. The agreed flow is an offline local wake phrase followed by ChatGPT Desktop's native Voice experience in a Codex task. Axiom should not own the AI conversation or reproduce ChatGPT's speech capture and output.

OpenAI's user documentation says Voice in Work or Codex on desktop can be started with a shortcut configured in Settings: [ChatGPT Work and Codex](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex). It does not document accepted key combinations. Axiom uses `CTRL+SHIFT+ALT+S` as its default; the same chord must be configured in ChatGPT Desktop or overridden in Axiom's settings.

## Decision

- Axiom listens for `Hey Axiom` using a local, offline wake-word engine.
- On detection, Axiom sends the user-configured ChatGPT Desktop Voice shortcut.
- ChatGPT Desktop handles conversation capture, AI responses, and speech output.
- Axiom only captures microphone input for wake-word detection and uses the Windows-selected default input device.
- Axiom does not implement a separate AI provider, STT, TTS, desktop UI inspection, or undocumented Codex API integration.
- The shortcut chord is stored in Axiom's user-level TOML settings and must match ChatGPT Desktop Settings > Voice.

## Consequences

- The device-independent runtime can be implemented before the SP96 arrives.
- Axiom needs the ChatGPT Desktop app running with a Codex task ready.
- The same shortcut must be configured in both ChatGPT Desktop and Axiom.
- ChatGPT Desktop's shortcut behavior, including background operation and duplicate-trigger semantics, must be validated on the target app version.
- Axiom cannot know whether the external Voice session is active or ended unless the desktop app later provides a supported signal.

## Revisit when

- ChatGPT Desktop changes the user-facing Voice shortcut workflow.
- A supported public interface becomes available for Voice lifecycle status.
- The product's first-use scenario changes away from ChatGPT Desktop Voice.
