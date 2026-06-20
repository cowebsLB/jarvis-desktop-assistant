from desktop_voice_assistant.config import Settings
from desktop_voice_assistant.model_manager import ModelManager


def test_warms_faster_whisper_model(monkeypatch) -> None:
    settings = Settings(stt_model_name="base.en", stt_device="cpu", stt_compute_type="int8")
    manager = ModelManager(settings)
    calls: list[tuple[str, str, str]] = []

    class FakeWhisperModel:
        def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
            calls.append((model_name, device, compute_type))

    monkeypatch.setattr("faster_whisper.WhisperModel", FakeWhisperModel)
    model_name = manager.install_stt_model()

    assert model_name == "base.en"
    assert calls == [("base.en", "cpu", "int8")]
