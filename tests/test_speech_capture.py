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
