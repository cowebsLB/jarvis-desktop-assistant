from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import RuntimeState


@dataclass
class StateTransition:
    previous: RuntimeState
    current: RuntimeState
    reason: str | None = None
    correlation_id: str | None = None
    conversation_id: str | None = None


TransitionCallback = Callable[[StateTransition], None]


class StateManager:
    _ALLOWED_TRANSITIONS: dict[RuntimeState, set[RuntimeState]] = {
        RuntimeState.BOOTING: {RuntimeState.IDLE, RuntimeState.ERROR, RuntimeState.SHUTTING_DOWN},
        RuntimeState.IDLE: {
            RuntimeState.WAKE_LISTENING,
            RuntimeState.CAPTURING_COMMAND,
            RuntimeState.UNDERSTANDING,
            RuntimeState.TRANSCRIBING,
            RuntimeState.EXECUTING,
            RuntimeState.ERROR,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.WAKE_LISTENING: {
            RuntimeState.CAPTURING_COMMAND,
            RuntimeState.UNDERSTANDING,
            RuntimeState.IDLE,
            RuntimeState.EXECUTING,
            RuntimeState.ERROR,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.CAPTURING_COMMAND: {RuntimeState.TRANSCRIBING, RuntimeState.ERROR},
        RuntimeState.TRANSCRIBING: {RuntimeState.UNDERSTANDING, RuntimeState.ERROR, RuntimeState.IDLE, RuntimeState.SHUTTING_DOWN},
        RuntimeState.UNDERSTANDING: {
            RuntimeState.PLANNING,
            RuntimeState.EXECUTING,
            RuntimeState.SPEAKING,
            RuntimeState.AWAITING_CONFIRMATION,
            RuntimeState.CLARIFYING,
            RuntimeState.ERROR,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.PLANNING: {
            RuntimeState.RESEARCHING,
            RuntimeState.EXECUTING,
            RuntimeState.AWAITING_CONFIRMATION,
            RuntimeState.CLARIFYING,
            RuntimeState.SPEAKING,
            RuntimeState.ERROR,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.RESEARCHING: {RuntimeState.FETCHING_SOURCES, RuntimeState.SPEAKING, RuntimeState.ERROR, RuntimeState.SHUTTING_DOWN},
        RuntimeState.FETCHING_SOURCES: {RuntimeState.RANKING_SOURCES, RuntimeState.SPEAKING, RuntimeState.ERROR, RuntimeState.SHUTTING_DOWN},
        RuntimeState.RANKING_SOURCES: {RuntimeState.SUMMARIZING_SOURCES, RuntimeState.SPEAKING, RuntimeState.ERROR, RuntimeState.SHUTTING_DOWN},
        RuntimeState.SUMMARIZING_SOURCES: {RuntimeState.ARCHIVING_SOURCES, RuntimeState.SPEAKING, RuntimeState.ERROR, RuntimeState.SHUTTING_DOWN},
        RuntimeState.ARCHIVING_SOURCES: {RuntimeState.SPEAKING, RuntimeState.ERROR, RuntimeState.SHUTTING_DOWN},
        RuntimeState.AWAITING_CONFIRMATION: {
            RuntimeState.SPEAKING,
            RuntimeState.UNDERSTANDING,
            RuntimeState.EXECUTING,
            RuntimeState.TRANSCRIBING,
            RuntimeState.IDLE,
            RuntimeState.ERROR,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.CLARIFYING: {
            RuntimeState.SPEAKING,
            RuntimeState.UNDERSTANDING,
            RuntimeState.TRANSCRIBING,
            RuntimeState.IDLE,
            RuntimeState.ERROR,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.EXECUTING: {RuntimeState.SPEAKING, RuntimeState.IDLE, RuntimeState.ERROR, RuntimeState.SHUTTING_DOWN},
        RuntimeState.SPEAKING: {
            RuntimeState.AWAITING_FOLLOWUP,
            RuntimeState.AWAITING_CONFIRMATION,
            RuntimeState.CLARIFYING,
            RuntimeState.WAKE_LISTENING,
            RuntimeState.IDLE,
            RuntimeState.ERROR,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.AWAITING_FOLLOWUP: {
            RuntimeState.CAPTURING_COMMAND,
            RuntimeState.UNDERSTANDING,
            RuntimeState.TRANSCRIBING,
            RuntimeState.WAKE_LISTENING,
            RuntimeState.IDLE,
            RuntimeState.ERROR,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.ERROR: {
            RuntimeState.SPEAKING,
            RuntimeState.IDLE,
            RuntimeState.WAKE_LISTENING,
            RuntimeState.SHUTTING_DOWN,
        },
        RuntimeState.SHUTTING_DOWN: set(),
    }

    def __init__(self, initial_state: RuntimeState = RuntimeState.BOOTING, on_transition: TransitionCallback | None = None) -> None:
        self._state = initial_state
        self._on_transition = on_transition

    @property
    def current(self) -> RuntimeState:
        return self._state

    def transition(
        self,
        new_state: RuntimeState,
        *,
        reason: str | None = None,
        correlation_id: str | None = None,
        conversation_id: str | None = None,
    ) -> StateTransition:
        previous = self._state
        if new_state == previous:
            transition = StateTransition(previous, new_state, reason, correlation_id, conversation_id)
            if self._on_transition:
                self._on_transition(transition)
            return transition

        allowed = self._ALLOWED_TRANSITIONS.get(previous, set())
        if new_state not in allowed:
            raise ValueError(f"Invalid state transition: {previous.value} -> {new_state.value}")
        self._state = new_state
        transition = StateTransition(previous, new_state, reason, correlation_id, conversation_id)
        if self._on_transition:
            self._on_transition(transition)
        return transition
