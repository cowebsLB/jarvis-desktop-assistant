import os
from pathlib import Path

from desktop_voice_assistant.actions import ActionExecutor
from desktop_voice_assistant.app_memory import AppMemoryStore
from desktop_voice_assistant.config import Settings
from desktop_voice_assistant.filesystem_actions import FileMatch
from desktop_voice_assistant.models import IntentResult


def test_unmatched_target_returns_discovery_failure() -> None:
    settings = Settings(app_allowlist={"notepad": "notepad.exe"}, site_allowlist={})
    result = ActionExecutor(settings).execute(IntentResult("open_target", 0.9, {"target": "totally fake app name"}))
    assert not result.success
    assert "couldn't match it" in result.spoken_reply


def test_unsupported_intent_returns_safe_failure() -> None:
    settings = Settings()
    result = ActionExecutor(settings).execute(IntentResult("unsupported", 0.1, {"query": "format disk"}))
    assert not result.success
    assert "not supported" in result.message.lower()


def test_open_target_normalizes_spoken_name(monkeypatch) -> None:
    settings = Settings(app_allowlist={"calculator": "calc.exe"}, site_allowlist={})
    launched: list[tuple[str, str]] = []

    monkeypatch.setattr(ActionExecutor, "_launch_target", staticmethod(lambda target, spoken_name: launched.append((target, spoken_name))))
    result = ActionExecutor(settings).execute(IntentResult("open_target", 0.9, {"target": "the calculator up"}))
    assert result.success
    assert launched == [("calc.exe", "calculator")]


def test_open_chrome_falls_back_to_browser_when_path_missing(monkeypatch) -> None:
    settings = Settings(app_allowlist={"chrome": r"C:\Missing\Chrome.exe"}, site_allowlist={})
    opened: list[str] = []

    monkeypatch.setattr(os.path, "exists", lambda path: False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(os, "startfile", lambda target: opened.append(target), raising=False)

    result = ActionExecutor(settings).execute(IntentResult("open_target", 0.9, {"target": "chrome"}))
    assert result.success
    assert opened == ["https://www.google.com"]


def test_open_target_uses_installed_app_resolution(monkeypatch) -> None:
    settings = Settings(app_allowlist={}, site_allowlist={})
    launched: list[tuple[str, str]] = []

    monkeypatch.setattr(ActionExecutor, "_resolve_installed_app", lambda self, target: r"C:\Apps\Code.exe")
    monkeypatch.setattr(ActionExecutor, "_launch_target", staticmethod(lambda target, spoken_name: launched.append((target, spoken_name))))

    result = ActionExecutor(settings).execute(IntentResult("open_target", 0.9, {"target": "vs code"}))
    assert result.success
    assert launched == [(r"C:\Apps\Code.exe", "visual studio code")]


def test_find_start_menu_shortcut_matches_target(monkeypatch, tmp_path: Path) -> None:
    appdata = tmp_path / "AppData"
    start_menu = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start_menu.mkdir(parents=True)
    shortcut = start_menu / "Visual Studio Code.lnk"
    shortcut.write_text("fake", encoding="utf-8")

    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path / "ProgramData"))

    result = ActionExecutor._find_start_menu_shortcut("visual studio code")
    assert result == shortcut


def test_fuzzy_match_opens_installed_app_and_learns_alias(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(app_allowlist={}, site_allowlist={})
    action = ActionExecutor(settings)
    action.memory = AppMemoryStore(tmp_path / "app_memory.json")
    launched: list[tuple[str, str]] = []

    monkeypatch.setattr(action, "_installed_app_catalog", lambda: ["spotify"])
    monkeypatch.setattr(action, "_resolve_installed_app", lambda target: r"C:\Apps\Spotify.exe" if target == "spotify" else None)
    monkeypatch.setattr(ActionExecutor, "_launch_target", staticmethod(lambda target, spoken_name: launched.append((target, spoken_name))))

    result = action.execute(IntentResult("open_target", 0.9, {"target": "spotfy"}))
    assert result.success
    assert launched == [(r"C:\Apps\Spotify.exe", "spotify")]
    assert action.memory.resolve("spotfy") == "spotify"


def test_calculate_expression_returns_result() -> None:
    result = ActionExecutor(Settings()).execute(IntentResult("calculate", 0.95, {"expression": "12 divided by 3"}))
    assert result.success
    assert result.message.endswith("= 4")


def test_clipboard_copy_dispatches_ctrl_c(monkeypatch) -> None:
    action = ActionExecutor(Settings())
    pressed: list[tuple[str, str]] = []

    class FakePyAutoGui:
        def hotkey(self, *keys) -> None:
            pressed.append(keys)

    monkeypatch.setattr(action, "_get_pyautogui", lambda: FakePyAutoGui())

    result = action.execute(IntentResult("clipboard_copy", 0.95, {}))
    assert result.success
    assert pressed == [("ctrl", "c")]


def test_clipboard_paste_dispatches_ctrl_v(monkeypatch) -> None:
    action = ActionExecutor(Settings())
    pressed: list[tuple[str, str]] = []

    class FakePyAutoGui:
        def hotkey(self, *keys) -> None:
            pressed.append(keys)

    monkeypatch.setattr(action, "_get_pyautogui", lambda: FakePyAutoGui())

    result = action.execute(IntentResult("clipboard_paste", 0.95, {}))
    assert result.success
    assert pressed == [("ctrl", "v")]


def test_clipboard_read_returns_text(monkeypatch) -> None:
    action = ActionExecutor(Settings())
    monkeypatch.setattr(action, "_get_clipboard_text", lambda: "clipboard contents")

    result = action.execute(IntentResult("clipboard_read", 0.95, {}))
    assert result.success
    assert result.spoken_reply == "clipboard contents"


def test_clipboard_save_note_writes_file(monkeypatch, tmp_path: Path) -> None:
    action = ActionExecutor(Settings())
    note_path = tmp_path / "clipboard-notes.md"
    monkeypatch.setattr(action, "_get_clipboard_text", lambda: "remember this")
    monkeypatch.setattr(action, "_clipboard_note_path", lambda: note_path)

    result = action.execute(IntentResult("clipboard_save_note", 0.95, {}))
    assert result.success
    assert note_path.exists()
    assert "remember this" in note_path.read_text(encoding="utf-8")


def test_clipboard_save_note_handles_empty_clipboard(monkeypatch) -> None:
    action = ActionExecutor(Settings())
    monkeypatch.setattr(action, "_get_clipboard_text", lambda: "")

    result = action.execute(IntentResult("clipboard_save_note", 0.95, {}))
    assert not result.success
    assert "clipboard is empty" in result.message.lower()


def test_focus_target_activates_visible_window(monkeypatch) -> None:
    action = ActionExecutor(Settings())

    class FakeCompletedProcess:
        def __init__(self) -> None:
            self.returncode = 0
            self.stdout = "Notepad"
            self.stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: FakeCompletedProcess())

    result = action.execute(IntentResult("focus_target", 0.94, {"target": "notepad"}))
    assert result.success
    assert "focused window" in result.message.lower()


def test_focus_target_returns_safe_failure_when_missing(monkeypatch) -> None:
    action = ActionExecutor(Settings())

    class FakeCompletedProcess:
        def __init__(self) -> None:
            self.returncode = 3
            self.stdout = ""
            self.stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: FakeCompletedProcess())

    result = action.execute(IntentResult("focus_target", 0.94, {"target": "notepad"}))
    assert not result.success
    assert "couldn't find a visible window" in result.spoken_reply.lower()


def test_switch_window_next_dispatches_alt_tab(monkeypatch) -> None:
    action = ActionExecutor(Settings())
    pressed: list[tuple[str, ...]] = []

    class FakePyAutoGui:
        def hotkey(self, *keys) -> None:
            pressed.append(keys)

    monkeypatch.setattr(action, "_get_pyautogui", lambda: FakePyAutoGui())

    result = action.execute(IntentResult("switch_window", 0.95, {"direction": "next"}))
    assert result.success
    assert pressed == [("alt", "tab")]


def test_switch_window_previous_dispatches_reverse_alt_tab(monkeypatch) -> None:
    action = ActionExecutor(Settings())
    pressed: list[tuple[str, ...]] = []

    class FakePyAutoGui:
        def hotkey(self, *keys) -> None:
            pressed.append(keys)

    monkeypatch.setattr(action, "_get_pyautogui", lambda: FakePyAutoGui())

    result = action.execute(IntentResult("switch_window", 0.95, {"direction": "previous"}))
    assert result.success
    assert pressed == [("alt", "shift", "tab")]


def test_open_folder_uses_known_alias(monkeypatch, tmp_path: Path) -> None:
    settings = Settings()
    action = ActionExecutor(settings)
    opened: list[str] = []
    folder = tmp_path / "Downloads"
    folder.mkdir()

    monkeypatch.setattr(action.desktop, "resolve_folder", lambda target: folder)
    monkeypatch.setattr(os, "startfile", lambda target: opened.append(target), raising=False)

    result = action.execute(IntentResult("open_folder", 0.95, {"target": "downloads"}))
    assert result.success
    assert opened == [str(folder)]


def test_open_file_uses_best_match(monkeypatch, tmp_path: Path) -> None:
    settings = Settings()
    action = ActionExecutor(settings)
    opened: list[str] = []
    matched = tmp_path / "budget-report.xlsx"

    monkeypatch.setattr(
        action.desktop,
        "search_file",
        lambda target, limit=1: [FileMatch(path=matched, score=0.95)],
    )
    monkeypatch.setattr(os, "startfile", lambda target: opened.append(target), raising=False)

    result = action.execute(IntentResult("open_file", 0.92, {"target": "budget report"}))
    assert result.success
    assert opened == [str(matched)]


def test_open_file_returns_safe_failure_when_missing(monkeypatch) -> None:
    action = ActionExecutor(Settings())
    monkeypatch.setattr(action.desktop, "search_file", lambda target, limit=1: [])

    result = action.execute(IntentResult("open_file", 0.92, {"target": "totally missing file"}))
    assert not result.success
    assert "couldn't find a local file" in result.spoken_reply.lower()


def test_browser_hotkeys_dispatch(monkeypatch) -> None:
    action = ActionExecutor(Settings())
    pressed: list[tuple[str, ...]] = []

    class FakePyAutoGui:
        def hotkey(self, *keys) -> None:
            pressed.append(keys)

    monkeypatch.setattr(action, "_get_pyautogui", lambda: FakePyAutoGui())

    # next tab
    result = action.execute(IntentResult("browser_tab_next", 0.95, {}))
    assert result.success
    assert pressed[-1] == ("ctrl", "tab")

    # previous tab
    result = action.execute(IntentResult("browser_tab_prev", 0.95, {}))
    assert result.success
    assert pressed[-1] == ("ctrl", "shift", "tab")

    # new tab
    result = action.execute(IntentResult("browser_tab_new", 0.95, {}))
    assert result.success
    assert pressed[-1] == ("ctrl", "t")

    # close tab
    result = action.execute(IntentResult("browser_tab_close", 0.95, {}))
    assert result.success
    assert pressed[-1] == ("ctrl", "w")

    # go back
    result = action.execute(IntentResult("browser_back", 0.95, {}))
    assert result.success
    assert pressed[-1] == ("alt", "left")

    # go forward
    result = action.execute(IntentResult("browser_forward", 0.95, {}))
    assert result.success
    assert pressed[-1] == ("alt", "right")

    # refresh page
    result = action.execute(IntentResult("browser_refresh", 0.95, {}))
    assert result.success
    assert pressed[-1] == ("f5",)

