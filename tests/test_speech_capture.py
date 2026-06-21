import numpy as np

from desktop_voice_assistant.speech import SpeechToText


def test_record_until_silence_returns_empty_when_no_audio(monkeypatch) -> None:
    class FakeInputStream:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    times = iter([0.0, 0.1, 0.2, 9.0])
    monkeypatch.setattr("sounddevice.InputStream", FakeInputStream)
    monkeypatch.setattr("time.monotonic", lambda: next(times))

    recording, audio_seconds, ended_early = SpeechToText._record_until_silence(
        sample_rate=16000,
        max_seconds=8.0,
        min_seconds=1.5,
        silence_timeout=1.0,
        speech_threshold=450,
        input_device=None,
    )
    assert isinstance(recording, np.ndarray)
    assert audio_seconds == 0.0
    assert ended_early is False


def test_resolve_microphone_device(monkeypatch) -> None:
    from desktop_voice_assistant.speech import resolve_microphone_device
    
    assert resolve_microphone_device(None) is None
    assert resolve_microphone_device(2) == 2
    
    import sounddevice as sd
    monkeypatch.setattr(sd, "query_devices", lambda: [
        {"name": "Default Device", "max_input_channels": 2},
        {"name": "Ambiguous Mic", "max_input_channels": 1},
        {"name": "Ambiguous Mic", "max_input_channels": 2},
        {"name": "Output Only", "max_input_channels": 0},
    ])
    
    assert resolve_microphone_device("Ambiguous Mic") == 1
    assert resolve_microphone_device("Default Device") == 0
    assert resolve_microphone_device("Unknown Device") is None
