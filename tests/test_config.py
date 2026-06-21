from pathlib import Path

from desktop_voice_assistant.config import Settings


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(wake_word_enabled=False, speech_rate=210, hud_enabled=False, hud_position_x=120, hud_position_y=80)
    settings.save(path)
    loaded = Settings.load(path)
    assert loaded.wake_word_enabled is False
    assert loaded.speech_rate == 210
    assert loaded.hud_enabled is False
    assert loaded.hud_position_x == 120
    assert loaded.hud_position_y == 80
    assert loaded.assistant_name == "Jarvis"


def test_settings_ui_instantiation() -> None:
    import tkinter as tk
    from desktop_voice_assistant.settings_ui import SettingsPanel
    root = tk.Tk()
    root.withdraw()
    settings = Settings()
    panel = SettingsPanel(root, settings)
    assert panel.assistant_name_var.get() == "Jarvis"
    assert panel.default_location_var.get() == "Beirut, Lebanon"
    assert panel.mic_device_var.get() == "Default"
    root.destroy()


def test_settings_ui_saves_mic_device() -> None:
    import tkinter as tk
    from desktop_voice_assistant.settings_ui import SettingsPanel
    root = tk.Tk()
    root.withdraw()
    settings = Settings(microphone_device=None)
    panel = SettingsPanel(root, settings)
    panel.mic_device_var.set("Test Microphone")
    panel._save_settings()
    assert settings.microphone_device == "Test Microphone"

