# Axiom Roadmap

**Status:** Draft

## Stage 0: Product and integration design

- Confirm the product identity, first-use scenario, and privacy defaults.
- Define the boundary between Axiom's own voice session and Codex Desktop voice.
- Document device assumptions without relying on attached production hardware.

**Exit criteria:** Architecture boundaries and unresolved decisions are visible and agreed.

## Stage 1: Python package foundation

- Create the `axiom` package and console entry point.
- Add configuration loading and structured diagnostics.
- Keep imports side-effect free and make device/provider modules replaceable.
- Add a Codex Desktop status and native voice handoff command.
- Add the runtime state machine, async audio contracts, and Windows launcher script.

**Exit criteria:** The device-independent wake/conversation flow is defined, and `axiom run` reports missing adapters without opening audio or keeping an empty process alive.

## Stage 2: Windows-default audio backend

- Implement the `AudioIO` contract using Windows-selected default input and output.
- Bridge audio callbacks into the async frame iterator safely.
- Keep input and output stream status separate, while leaving device choice to Windows Sound Settings.
- Validate capture, playback, reconnect, and default-device changes after the SP96 arrives and is selected in Windows.

**Exit criteria:** On the target machine, Axiom uses the Windows-selected default input and output without a device inventory or selection flow, and recovers cleanly when those streams become unavailable.

## Stage 3: Codex Desktop voice handoff

- Detect whether ChatGPT Desktop is running where practical.
- Report that native voice must be started inside a Codex task unless a supported external interface is documented.
- Verify account/workspace rollout and task behavior manually on the target installation.
- Keep this adapter independent from the Axiom voice provider.

**Exit criteria:** The product gives accurate readiness guidance and does not depend on undocumented UI automation.

## Stage 4: Axiom voice companion

- Add an explicit foreground capture mode before enabling always-on wake-word listening.
- Select and integrate a local wake-word engine for `Hey Axiom`.
- Add a real-time voice provider, interruption handling, spoken responses, and clear listening/speaking states.
- Exercise the full audio path with the SP96 on the target machine.

**Exit criteria:** Axiom can complete a private, interruptible spoken English-practice session and can stop listening immediately on user request.

## Stage 5: Home assistant capabilities

- Add capability modules behind explicit permission boundaries.
- Add durable preferences only after choosing a storage and deletion model.
- Add integrations one at a time with visible status and user-controlled access.

**Exit criteria:** New capabilities do not couple device capture, wake-word detection, or the conversation provider to a single service.

## Release principle

Do not label the application production-ready until audio behavior, permissions, error handling, and long-running reliability have been checked on the actual target machine and hardware.
