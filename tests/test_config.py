from pathlib import Path

from desktop_voice_assistant.config import Settings


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(wake_word_enabled=False, speech_rate=210)
    settings.save(path)
    loaded = Settings.load(path)
    assert loaded.wake_word_enabled is False
    assert loaded.speech_rate == 210
    assert loaded.assistant_name == "Jarvis"
