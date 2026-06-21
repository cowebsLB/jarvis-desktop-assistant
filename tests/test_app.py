import pytest
import sys
from desktop_voice_assistant.app import acquire_lock, main

def test_acquire_lock() -> None:
    # First acquisition should succeed
    sock1 = acquire_lock(port=59991)
    assert sock1 is not None

    # Second acquisition on the same port should fail
    sock2 = acquire_lock(port=59991)
    assert sock2 is None

    # After closing the first socket, it should succeed again
    sock1.close()
    sock3 = acquire_lock(port=59991)
    assert sock3 is not None
    sock3.close()

def test_main_exits_if_locked(monkeypatch) -> None:
    # Force acquire_lock to return None to simulate lock collision
    monkeypatch.setattr("desktop_voice_assistant.app.acquire_lock", lambda port=47711: None)

    exited = False
    exit_code = -1

    def mock_exit(code):
        nonlocal exited, exit_code
        exited = True
        exit_code = code
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", mock_exit)
    monkeypatch.setattr("desktop_voice_assistant.app.configure_logging", lambda: "fake_log.log")

    with pytest.raises(SystemExit):
        main()

    assert exited is True
    assert exit_code == 0
