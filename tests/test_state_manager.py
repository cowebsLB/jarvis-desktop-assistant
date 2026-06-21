import pytest

from desktop_voice_assistant.models import RuntimeState
from desktop_voice_assistant.state_manager import StateManager


def test_state_manager_allows_valid_transition_chain() -> None:
    manager = StateManager()

    manager.transition(RuntimeState.IDLE)
    manager.transition(RuntimeState.WAKE_LISTENING)
    manager.transition(RuntimeState.CAPTURING_COMMAND)
    manager.transition(RuntimeState.TRANSCRIBING)
    manager.transition(RuntimeState.UNDERSTANDING)
    manager.transition(RuntimeState.PLANNING)
    manager.transition(RuntimeState.EXECUTING)
    manager.transition(RuntimeState.SPEAKING)
    manager.transition(RuntimeState.AWAITING_FOLLOWUP)

    assert manager.current == RuntimeState.AWAITING_FOLLOWUP


def test_state_manager_rejects_invalid_transition() -> None:
    manager = StateManager()

    with pytest.raises(ValueError):
        manager.transition(RuntimeState.SPEAKING)


def test_state_manager_allows_research_early_exit_to_speaking() -> None:
    manager = StateManager()

    manager.transition(RuntimeState.IDLE)
    manager.transition(RuntimeState.TRANSCRIBING)
    manager.transition(RuntimeState.UNDERSTANDING)
    manager.transition(RuntimeState.PLANNING)
    manager.transition(RuntimeState.RESEARCHING)
    manager.transition(RuntimeState.FETCHING_SOURCES)
    manager.transition(RuntimeState.SPEAKING)

    assert manager.current == RuntimeState.SPEAKING


def test_state_manager_allows_confirmation_and_clarification_reset_to_wake_listening() -> None:
    # AWAITING_CONFIRMATION -> WAKE_LISTENING
    manager1 = StateManager(RuntimeState.AWAITING_CONFIRMATION)
    manager1.transition(RuntimeState.WAKE_LISTENING)
    assert manager1.current == RuntimeState.WAKE_LISTENING

    # CLARIFYING -> WAKE_LISTENING
    manager2 = StateManager(RuntimeState.CLARIFYING)
    manager2.transition(RuntimeState.WAKE_LISTENING)
    assert manager2.current == RuntimeState.WAKE_LISTENING

    # AWAITING_CONFIRMATION -> CAPTURING_COMMAND
    manager3 = StateManager(RuntimeState.AWAITING_CONFIRMATION)
    manager3.transition(RuntimeState.CAPTURING_COMMAND)
    assert manager3.current == RuntimeState.CAPTURING_COMMAND

    # CLARIFYING -> CAPTURING_COMMAND
    manager4 = StateManager(RuntimeState.CLARIFYING)
    manager4.transition(RuntimeState.CAPTURING_COMMAND)
    assert manager4.current == RuntimeState.CAPTURING_COMMAND
