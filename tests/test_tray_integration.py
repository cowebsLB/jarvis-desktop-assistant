import pytest
from unittest.mock import MagicMock, patch
from desktop_voice_assistant.config import Settings
from desktop_voice_assistant.tray import TrayApplication
from desktop_voice_assistant.models import RuntimeState
from desktop_voice_assistant.speech import MissingTextToSpeech

def test_tray_listeners_sync_ptt_enabled():
    settings = Settings(push_to_talk_enabled=True, wake_word_enabled=True)
    assistant = MagicMock()
    assistant.runtime_state = RuntimeState.WAKE_LISTENING
    
    with patch("desktop_voice_assistant.tray.WakeWordListener") as mock_ww_class:
        mock_ww = mock_ww_class.return_value
        tray = TrayApplication(assistant, settings)
        
        tray._start_ptt_listener = MagicMock()
        tray._stop_ptt_listener = MagicMock()
        
        tray._sync_listeners(reason="test")
        
        mock_ww.stop.assert_called_once()
        tray._start_ptt_listener.assert_called_once()
        assistant.set_runtime_state.assert_called_with(RuntimeState.IDLE, reason="test: PTT active")

def test_tray_listeners_sync_wake_word_enabled():
    settings = Settings(push_to_talk_enabled=False, wake_word_enabled=True)
    assistant = MagicMock()
    assistant.runtime_state = RuntimeState.IDLE
    
    with patch("desktop_voice_assistant.tray.WakeWordListener") as mock_ww_class:
        mock_ww = mock_ww_class.return_value
        mock_ww.ready = True
        tray = TrayApplication(assistant, settings)
        
        tray._start_ptt_listener = MagicMock()
        tray._stop_ptt_listener = MagicMock()
        
        tray._sync_listeners(reason="test")
        
        tray._stop_ptt_listener.assert_called_once()
        mock_ww.start.assert_called_once()
        assistant.set_runtime_state.assert_called_with(RuntimeState.WAKE_LISTENING, reason="test: wake word active")

def test_tray_listeners_sync_both_disabled():
    settings = Settings(push_to_talk_enabled=False, wake_word_enabled=False)
    assistant = MagicMock()
    assistant.runtime_state = RuntimeState.WAKE_LISTENING
    
    with patch("desktop_voice_assistant.tray.WakeWordListener") as mock_ww_class:
        mock_ww = mock_ww_class.return_value
        tray = TrayApplication(assistant, settings)
        
        tray._start_ptt_listener = MagicMock()
        tray._stop_ptt_listener = MagicMock()
        
        tray._sync_listeners(reason="test")
        
        tray._stop_ptt_listener.assert_called_once()
        mock_ww.stop.assert_called_once()
        assistant.set_runtime_state.assert_called_with(RuntimeState.IDLE, reason="test: wake word disabled")

def test_tray_toggle_wake_word():
    settings = Settings(push_to_talk_enabled=False, wake_word_enabled=True)
    assistant = MagicMock()
    
    with patch("desktop_voice_assistant.tray.WakeWordListener") as mock_ww_class:
        tray = TrayApplication(assistant, settings)
        tray._sync_listeners = MagicMock()
        tray.settings.save = MagicMock()
        
        tray._toggle_wake_word(None, None)
        assert settings.wake_word_enabled is False
        tray._sync_listeners.assert_called_with(reason="toggle wake word")

def test_tray_quit():
    settings = Settings()
    assistant = MagicMock()
    
    with patch("desktop_voice_assistant.tray.WakeWordListener") as mock_ww_class:
        mock_ww = mock_ww_class.return_value
        tray = TrayApplication(assistant, settings)
        tray._stop_ptt_listener = MagicMock()
        tray.icon = MagicMock()
        
        tray._quit(None, None)
        mock_ww.stop.assert_called_once()
        tray._stop_ptt_listener.assert_called_once()
        assistant.set_runtime_state.assert_called_with(RuntimeState.SHUTTING_DOWN, reason="tray quit requested")
        tray.icon.stop.assert_called_once()

def test_tray_on_settings_saved_tts_engine_none():
    settings = Settings(tts_engine="none")
    assistant = MagicMock()
    
    with patch("desktop_voice_assistant.tray.WakeWordListener") as mock_ww_class:
        tray = TrayApplication(assistant, settings)
        tray._sync_listeners = MagicMock()
        
        tray._on_settings_saved()
        assert isinstance(assistant.tts, MissingTextToSpeech)

def test_tray_on_settings_saved_tts_engine_pyttsx3():
    settings = Settings(tts_engine="pyttsx3")
    assistant = MagicMock()
    
    with patch("desktop_voice_assistant.tray.WakeWordListener") as mock_ww_class, \
         patch("desktop_voice_assistant.tray.TextToSpeech") as mock_tts_class:
        tray = TrayApplication(assistant, settings)
        tray._sync_listeners = MagicMock()
        
        tray._on_settings_saved()
        mock_tts_class.assert_called_with(settings)

def test_tray_ptt_hotkey_threaded_starts():
    settings = Settings(push_to_talk_enabled=True)
    assistant = MagicMock()
    
    with patch("desktop_voice_assistant.tray.WakeWordListener") as mock_ww_class:
        tray = TrayApplication(assistant, settings)
        
        with patch("threading.Thread") as mock_thread:
            tray._start_ptt_listener()
            mock_thread.assert_called_once()
            
        # Stopping handles when _ptt_thread_id is set
        tray._ptt_thread_id = 1234
        with patch("desktop_voice_assistant.tray.user32") as mock_user32:
            tray._stop_ptt_listener()
            mock_user32.PostThreadMessageW.assert_called_once_with(1234, 18, 0, 0)
