"""Axiom runtime states and allowed transitions."""

from __future__ import annotations

from enum import StrEnum


class RuntimeState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    WAITING_FOR_WAKEWORD = "waiting_for_wakeword"
    TRIGGERING_CODEX_VOICE = "triggering_codex_voice"
    STOPPING = "stopping"


_ALLOWED_TRANSITIONS: dict[RuntimeState, frozenset[RuntimeState]] = {
    RuntimeState.STOPPED: frozenset({RuntimeState.STARTING}),
    RuntimeState.STARTING: frozenset(
        {RuntimeState.WAITING_FOR_WAKEWORD, RuntimeState.STOPPING}
    ),
    RuntimeState.WAITING_FOR_WAKEWORD: frozenset(
        {RuntimeState.TRIGGERING_CODEX_VOICE, RuntimeState.STOPPING}
    ),
    RuntimeState.TRIGGERING_CODEX_VOICE: frozenset(
        {RuntimeState.WAITING_FOR_WAKEWORD, RuntimeState.STOPPING}
    ),
    RuntimeState.STOPPING: frozenset({RuntimeState.STOPPED}),
}


class InvalidStateTransition(RuntimeError):
    """Raised when the runtime attempts an unsupported state transition."""


class RuntimeStateMachine:
    """Track and validate Axiom's background voice lifecycle."""

    def __init__(self) -> None:
        self._state = RuntimeState.STOPPED

    @property
    def state(self) -> RuntimeState:
        return self._state

    def transition(self, next_state: RuntimeState) -> None:
        if next_state not in _ALLOWED_TRANSITIONS[self._state]:
            raise InvalidStateTransition(
                f"Cannot move Axiom from {self._state.value} to {next_state.value}."
            )
        self._state = next_state
