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
