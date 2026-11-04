# ADR 0001: Codex Desktop Voice Boundary

- Status: Proposed
- Date: 2026-11-04

## Context

The initial project request includes voice control for Codex Desktop. ChatGPT Desktop supports voice conversations in Codex tasks through an in-app entry point. Public product documentation describes starting a voice chat in the desktop app, but does not document an external API for starting or controlling that session.

Axiom also has a broader product goal: a local wake phrase and an AI conversation that can later expand beyond coding tasks. Coupling Axiom's core session to undocumented desktop controls would make the product dependent on an unstable interface and would prevent independent voice sessions.

## Decision

- Treat Codex Desktop as an optional external voice surface behind an adapter.
- Start with readiness checks and a handoff guide for the documented in-app voice flow.
- Keep Axiom's own audio runtime and conversation provider independent.
- Add automated Codex Desktop control only if a documented, supported interface becomes available.
- Do not inject audio, text, or clicks into the desktop UI as the integration contract.

## Consequences

- The first integration milestone can be designed and developed before the SP96 arrives.
- Starting a Codex voice session may remain a user action in ChatGPT Desktop.
- Axiom's own always-available conversation remains possible without Codex Desktop.
- The adapter can evolve later without changing audio I/O or the conversation core.

## Revisit when

- OpenAI documents a supported external control interface for Codex Desktop voice.
- The required user journey is clarified as controlling an existing Codex task rather than using Axiom as a standalone voice companion.
