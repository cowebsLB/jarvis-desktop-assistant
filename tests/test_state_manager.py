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
