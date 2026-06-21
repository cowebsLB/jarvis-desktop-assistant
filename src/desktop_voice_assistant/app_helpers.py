from __future__ import annotations

import logging
import subprocess
import shutil
import time
from pathlib import Path

from .models import ActionResult

LOGGER = logging.getLogger(__name__)


class NotepadHelper:
    def __init__(self, executor) -> None:
        self.executor = executor

    def write_and_save(self, text: str, filename: str) -> ActionResult:
        pyautogui = self.executor._get_pyautogui()
        # 1. Try focusing Notepad; if not found, launch it
        focus_res = self.executor._focus_target("notepad")
        if not focus_res.success:
            path = shutil.which("notepad") or "notepad"
            subprocess.Popen([path], shell=False)
            time.sleep(1.2)
        else:
            time.sleep(0.5)

        # 2. Type the text
        pyautogui.write(text, interval=0.01)
        time.sleep(0.5)

        # 3. Save file using Ctrl+S
        pyautogui.hotkey("ctrl", "s")
        time.sleep(0.8)

        # 4. Type path (save in Documents)
        docs_dir = Path.home() / "Documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        cleaned_filename = filename
        for ext in ("txt", "log", "md", "json", "py", "csv"):
            if cleaned_filename.endswith(f" {ext}"):
                cleaned_filename = cleaned_filename[:-len(ext)-1] + f".{ext}"
                break
        else:
            if "." not in cleaned_filename:
                cleaned_filename += ".txt"
                
        save_path = docs_dir / cleaned_filename
        
        # Delete pre-filled text in save dialog by typing over it or sending backspace
        pyautogui.write(str(save_path))
        time.sleep(0.5)

        # 5. Confirm save
        pyautogui.press("enter")
        time.sleep(0.5)

        return ActionResult(
            True,
            f"Notepad written and saved as {filename} in Documents.",
            f"Note saved in Notepad as {filename}."
        )


class BrowserHelper:
    def __init__(self, executor) -> None:
        self.executor = executor

    def search_and_bookmark(self, query: str) -> ActionResult:
        pyautogui = self.executor._get_pyautogui()
        # 1. Launch/Focus Chrome or default browser and search
        self.executor._search_web(query)
        time.sleep(2.0)  # Wait for search page to load

        # 2. Bookmark the page with Ctrl+D
        pyautogui.hotkey("ctrl", "d")
        time.sleep(0.8)

        # 3. Press Enter to confirm bookmark
        pyautogui.press("enter")
        
        return ActionResult(
            True,
            f"Searched browser for '{query}' and bookmarked the page.",
            f"I have opened a search for {query} and bookmarked it."
        )

    def click_control(self, control_name: str) -> ActionResult:
        focus_res = self.executor._focus_target("chrome")
        if not focus_res.success:
            self.executor._focus_target("browser")
        time.sleep(0.8)
        
        # Try pywinauto first
        try:
            import pywinauto
            app = pywinauto.Application(backend="uia").connect(title_re=".*(Chrome|Browser).*", timeout=1)
            window = app.top_window()
            control = window.child_window(title=control_name, timeout=1)
            control.click_input()
            return ActionResult(
                True,
                f"Clicked browser control '{control_name}' using UI automation.",
                f"Clicked {control_name} on the browser."
            )
        except Exception:
            # Fall back to keyboard find mechanism
            pyautogui = self.executor._get_pyautogui()
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.5)
            pyautogui.write(control_name, interval=0.01)
            time.sleep(0.5)
            pyautogui.press("esc")
            time.sleep(0.3)
            pyautogui.press("enter")
            return ActionResult(
                True,
                f"Clicked browser control/text '{control_name}' via find shortcut.",
                f"Clicked {control_name} on the page."
            )

    def fill_form(self, form_data: dict[str, str] | str) -> ActionResult:
        focus_res = self.executor._focus_target("chrome")
        if not focus_res.success:
            self.executor._focus_target("browser")
        time.sleep(0.8)

        data = {}
        if isinstance(form_data, str):
            try:
                import json
                data = json.loads(form_data)
            except Exception:
                # Comma-separated pairs e.g. "Username: myuser, Password: mypassword"
                for pair in form_data.split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        data[k.strip()] = v.strip()
        else:
            data = form_data

        if not data:
            return ActionResult(False, "No form data provided.", "No fields to fill.")

        pyautogui = self.executor._get_pyautogui()
        for label, val in data.items():
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.5)
            pyautogui.write(label, interval=0.01)
            time.sleep(0.5)
            pyautogui.press("esc")
            time.sleep(0.3)
            pyautogui.press("tab")
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("backspace")
            time.sleep(0.1)
            pyautogui.write(val, interval=0.01)
            time.sleep(0.3)

        return ActionResult(
            True,
            f"Filled browser form fields: {list(data.keys())}",
            "Filled the requested fields on the browser page."
        )


class VSCodeHelper:
    def __init__(self, executor) -> None:
        self.executor = executor

    def open_terminal(self) -> ActionResult:
        pyautogui = self.executor._get_pyautogui()
        # 1. Focus VS Code
        focus_res = self.executor._focus_target("visual studio code")
        if not focus_res.success:
            # Try launch
            path = shutil.which("code") or "code"
            subprocess.Popen([path], shell=False)
            time.sleep(3.0)
        else:
            time.sleep(0.8)

        # 2. Trigger open terminal shortcut: ctrl+`
        pyautogui.hotkey("ctrl", "`")
        
        return ActionResult(
            True,
            "Focused Visual Studio Code and opened terminal pane.",
            "Visual Studio Code terminal is now open."
        )


class SpotifyHelper:
    def __init__(self, executor) -> None:
        self.executor = executor

    def play_pause(self) -> ActionResult:
        self.executor._focus_target("spotify")
        time.sleep(0.5)
        pyautogui = self.executor._get_pyautogui()
        pyautogui.press("space")
        return ActionResult(True, "Toggled Spotify playback.", "I toggled Spotify playback.")

    def next_track(self) -> ActionResult:
        self.executor._focus_target("spotify")
        time.sleep(0.5)
        pyautogui = self.executor._get_pyautogui()
        pyautogui.hotkey("ctrl", "right")
        return ActionResult(True, "Skipped to next Spotify track.", "Skipped to the next song.")

    def previous_track(self) -> ActionResult:
        self.executor._focus_target("spotify")
        time.sleep(0.5)
        pyautogui = self.executor._get_pyautogui()
        pyautogui.hotkey("ctrl", "left")
        return ActionResult(True, "Went to previous Spotify track.", "Went back to the previous song.")

    def volume_adjust(self, direction: str) -> ActionResult:
        self.executor._focus_target("spotify")
        time.sleep(0.5)
        pyautogui = self.executor._get_pyautogui()
        if direction == "up":
            pyautogui.hotkey("ctrl", "up")
            msg = "Increased Spotify volume."
        else:
            pyautogui.hotkey("ctrl", "down")
            msg = "Decreased Spotify volume."
        return ActionResult(True, msg, msg)


class DiscordHelper:
    def __init__(self, executor) -> None:
        self.executor = executor

    def mute_unmute(self) -> ActionResult:
        self.executor._focus_target("discord")
        time.sleep(0.5)
        pyautogui = self.executor._get_pyautogui()
        pyautogui.hotkey("ctrl", "shift", "m")
        return ActionResult(True, "Toggled Discord mute.", "Toggled mute on Discord.")

    def deafen(self) -> ActionResult:
        self.executor._focus_target("discord")
        time.sleep(0.5)
        pyautogui = self.executor._get_pyautogui()
        pyautogui.hotkey("ctrl", "shift", "d")
        return ActionResult(True, "Toggled Discord deafen.", "Toggled deafen on Discord.")

    def navigate_to(self, target: str) -> ActionResult:
        self.executor._focus_target("discord")
        time.sleep(0.8)
        pyautogui = self.executor._get_pyautogui()
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.5)
        pyautogui.write(target, interval=0.01)
        time.sleep(0.5)
        pyautogui.press("enter")
        return ActionResult(True, f"Navigated to Discord channel or user: {target}", f"Navigated to {target} in Discord.")


class SlackHelper:
    def __init__(self, executor) -> None:
        self.executor = executor

    def mute_unmute(self) -> ActionResult:
        self.executor._focus_target("slack")
        time.sleep(0.5)
        pyautogui = self.executor._get_pyautogui()
        pyautogui.hotkey("ctrl", "shift", "m")
        return ActionResult(True, "Toggled Slack mute.", "Toggled mute on Slack.")

    def navigate_to(self, target: str) -> ActionResult:
        self.executor._focus_target("slack")
        time.sleep(0.8)
        pyautogui = self.executor._get_pyautogui()
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.5)
        pyautogui.write(target, interval=0.01)
        time.sleep(0.5)
        pyautogui.press("enter")
        return ActionResult(True, f"Navigated to Slack channel or user: {target}", f"Navigated to {target} in Slack.")
