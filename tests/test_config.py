from pathlib import Path

from desktop_voice_assistant.config import Settings


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(
        wake_word_enabled=False,
        speech_rate=210,
        hud_enabled=False,
        hud_position_x=120,
        hud_position_y=80,
        assistant_style="concise",
        confirmation_policy="always",
        wake_cue_enabled=False,
        web_archive_enabled=False,
        archive_recall_limit=5,
        gemini_enabled=True,
        gemini_model="gemini-3.5-flash",
        tts_engine="none",
        push_to_talk_enabled=True,
        proactive_features_enabled=True,
    )
    settings.save(path)
    loaded = Settings.load(path)
    assert loaded.wake_word_enabled is False
    assert loaded.speech_rate == 210
    assert loaded.hud_enabled is False
    assert loaded.hud_position_x == 120
    assert loaded.hud_position_y == 80
    assert loaded.assistant_style == "concise"
    assert loaded.confirmation_policy == "always"
    assert loaded.wake_cue_enabled is False
    assert loaded.web_archive_enabled is False
    assert loaded.archive_recall_limit == 5
    assert loaded.gemini_enabled is True
    assert loaded.gemini_model == "gemini-3.5-flash"
    assert loaded.assistant_name == "Jarvis"
    assert loaded.tts_engine == "none"
    assert loaded.push_to_talk_enabled is True
    assert loaded.proactive_features_enabled is True


def test_settings_ui_instantiation() -> None:
    import tkinter as tk
    from desktop_voice_assistant.settings_ui import SettingsPanel
    root = tk.Tk()
    root.withdraw()
    settings = Settings()
    panel = SettingsPanel(root, settings)
    assert panel.assistant_name_var.get() == "Jarvis"
    assert panel.assistant_style_var.get() == "stark-butler"
    assert panel.default_location_var.get() == "Beirut, Lebanon"
    assert panel.mic_device_var.get() == SettingsPanel.AUTO_DETECT_MIC
    assert panel.gemini_enabled_var.get() is False
    assert panel.tts_engine_var.get() == "pyttsx3"
    assert panel.push_to_talk_enabled_var.get() is False
    assert panel.proactive_features_enabled_var.get() is False
    root.destroy()


def test_settings_ui_saves_mic_device(monkeypatch) -> None:
    import tkinter as tk
    from desktop_voice_assistant.settings_ui import SettingsPanel
    root = tk.Tk()
    root.withdraw()
    settings = Settings(microphone_device=None)
    monkeypatch.setattr(settings, "save", lambda path=None: None)
    panel = SettingsPanel(root, settings)
    panel.mic_device_var.set("Test Microphone")
    panel.assistant_style_var.set("neutral")
    panel.confirmation_policy_var.set("always")
    panel.wake_cue_var.set(False)
    panel.archive_enabled_var.set(False)
    panel.archive_recall_var.set(4)
    panel.gemini_enabled_var.set(True)
    panel.gemini_model_var.set("gemini-3.5-flash")
    panel.tts_engine_var.set("none")
    panel.push_to_talk_enabled_var.set(True)
    panel.proactive_features_enabled_var.set(True)
    panel._save_settings()
    assert settings.microphone_device == "Test Microphone"
    assert settings.assistant_style == "neutral"
    assert settings.confirmation_policy == "always"
    assert settings.wake_cue_enabled is False
    assert settings.web_archive_enabled is False
    assert settings.archive_recall_limit == 4
    assert settings.gemini_enabled is True
    assert settings.gemini_model == "gemini-3.5-flash"
    assert settings.tts_engine == "none"
    assert settings.push_to_talk_enabled is True
    assert settings.proactive_features_enabled is True


def test_settings_ui_falls_back_to_auto_detect_for_missing_saved_microphone() -> None:
    import tkinter as tk
    from desktop_voice_assistant.settings_ui import SettingsPanel

    root = tk.Tk()
    root.withdraw()
    settings = Settings(microphone_device="Missing Microphone")
    panel = SettingsPanel(root, settings)

    assert panel.mic_device_var.get() == SettingsPanel.AUTO_DETECT_MIC
    root.destroy()
