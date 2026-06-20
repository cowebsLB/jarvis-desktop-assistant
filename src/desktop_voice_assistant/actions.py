from __future__ import annotations

import ast
import difflib
import logging
import os
import re
import shutil
import subprocess
import webbrowser
import winreg
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote_plus

from .app_memory import AppMemoryStore
from .config import APP_DIR, Settings
from .filesystem_actions import DesktopControl
from .models import ActionResult, IntentResult, OpenTargetPreview
from .response_style import ResponseStyle


LOGGER = logging.getLogger(__name__)


class ActionExecutor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._pyautogui = None
        self.memory = AppMemoryStore()
        self.desktop = DesktopControl()

    def execute(self, intent: IntentResult) -> ActionResult:
        if intent.intent == "dictate":
            return self._type_text(intent.slots["text"])
        if intent.intent == "calculate":
            return self._calculate(intent.slots["expression"])
        if intent.intent == "clipboard_copy":
            return self._copy_selection()
        if intent.intent == "clipboard_paste":
            return self._paste_clipboard()
        if intent.intent == "clipboard_read":
            return self._read_clipboard()
        if intent.intent == "clipboard_save_note":
            return self._save_clipboard_to_note()
        if intent.intent == "focus_target":
            return self._focus_target(intent.slots["target"])
        if intent.intent == "switch_window":
            return self._switch_window(intent.slots.get("direction") or "next")
        if intent.intent == "open_target":
            return self._open_target(intent.slots["target"])
        if intent.intent == "open_folder":
            return self._open_folder(intent.slots["target"])
        if intent.intent == "open_file":
            return self._open_file(intent.slots["target"])
        if intent.intent == "open_source":
            return self._open_source(intent.slots["url"], intent.slots.get("title") or intent.slots["url"])
        if intent.intent == "web_search":
            return self._search_web(intent.slots["query"])
        if intent.intent == "unsupported":
            return ActionResult(
                False,
                "That request is not supported in this version.",
                "That request is not supported in this version.",
            )
        return ActionResult(False, "Unhandled intent.", "I couldn't handle that request.")

    def preview_open_target(self, target: str) -> OpenTargetPreview:
        spoken_target = self._normalize_target_name(target)
        resolved_target = self.memory.resolve(spoken_target) or spoken_target

        if resolved_target in self.settings.app_allowlist or resolved_target in self.settings.site_allowlist:
            return OpenTargetPreview(
                requested_target=spoken_target,
                resolved_target=resolved_target,
                exact_match=True,
                launchable=True,
            )

        if self._resolve_installed_app(resolved_target):
            return OpenTargetPreview(
                requested_target=spoken_target,
                resolved_target=resolved_target,
                exact_match=True,
                launchable=True,
            )

        fuzzy_target = self._fuzzy_match_installed_app(resolved_target)
        if fuzzy_target and self._resolve_installed_app(fuzzy_target):
            return OpenTargetPreview(
                requested_target=spoken_target,
                resolved_target=resolved_target,
                fuzzy_match=fuzzy_target,
                launchable=True,
            )

        return OpenTargetPreview(
            requested_target=spoken_target,
            resolved_target=resolved_target,
            launchable=False,
        )

    def _type_text(self, text: str) -> ActionResult:
        pyautogui = self._get_pyautogui()
        pyautogui.write(text, interval=0.01)
        return ActionResult(True, f"Typed: {text}", ResponseStyle.typed())

    def _calculate(self, expression: str) -> ActionResult:
        normalized = self._normalize_expression(expression)
        if not normalized:
            return ActionResult(False, "No calculation expression was provided.", "I need a calculation to work with.")
        try:
            value = self._safe_eval_expression(normalized)
        except (ValueError, ZeroDivisionError, SyntaxError):
            return ActionResult(
                False,
                f"Could not evaluate expression: {expression}",
                f"I heard {expression}, but I couldn't evaluate it safely.",
            )

        rendered = self._format_number(value)
        return ActionResult(
            True,
            f"Calculated {normalized} = {rendered}",
            ResponseStyle.calculation(normalized, rendered),
        )

    def _copy_selection(self) -> ActionResult:
        pyautogui = self._get_pyautogui()
        pyautogui.hotkey("ctrl", "c")
        return ActionResult(True, "Copied current selection.", ResponseStyle.clipboard_copied())

    def _paste_clipboard(self) -> ActionResult:
        pyautogui = self._get_pyautogui()
        pyautogui.hotkey("ctrl", "v")
        return ActionResult(True, "Pasted clipboard contents.", ResponseStyle.clipboard_pasted())

    def _read_clipboard(self) -> ActionResult:
        text = self._get_clipboard_text()
        if not text:
            return ActionResult(False, "Clipboard is empty.", ResponseStyle.clipboard_empty())
        return ActionResult(True, "Read clipboard contents.", text)

    def _save_clipboard_to_note(self) -> ActionResult:
        text = self._get_clipboard_text()
        if not text:
            return ActionResult(False, "Clipboard is empty.", ResponseStyle.clipboard_empty())
        note_path = self._clipboard_note_path()
        note_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        with note_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n## {timestamp}\n\n{text.strip()}\n")
        return ActionResult(
            True,
            f"Saved clipboard note to {note_path}",
            ResponseStyle.clipboard_saved_note(),
            opened_target=str(note_path),
        )

    def _focus_target(self, target: str) -> ActionResult:
        spoken_target = self._normalize_target_name(target)
        resolved_target = self.memory.resolve(spoken_target) or spoken_target
        candidates = self._focus_candidate_names(resolved_target)
        script = (
            "$target=$args[0];"
            "$candidateArg=$args[1];"
            "$candidates=@();"
            "if ($candidateArg) {$candidates=$candidateArg.Split(';')};"
            "$proc=Get-Process | Where-Object { $_.MainWindowTitle -and ("
            "$_.MainWindowTitle.ToLower().Contains($target) -or $candidates -contains $_.ProcessName.ToLower()) } | "
            "Sort-Object @{Expression={ if ($_.MainWindowTitle.ToLower().Contains($target)) {0} else {1} }}, MainWindowTitle | "
            "Select-Object -First 1;"
            "if (-not $proc) { exit 3 };"
            "$shell=New-Object -ComObject WScript.Shell;"
            "if ($shell.AppActivate($proc.Id)) { Write-Output $proc.MainWindowTitle; exit 0 };"
            "exit 4"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script, "--", resolved_target, ";".join(candidates)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return ActionResult(
                False,
                f"Could not focus target: {resolved_target}",
                f"I couldn't find a visible window for {resolved_target}.",
            )
        self.memory.remember(spoken_target, resolved_target)
        return ActionResult(
            True,
            f"Focused window: {resolved_target}",
            ResponseStyle.focusing(resolved_target),
            opened_target=resolved_target,
        )

    def _switch_window(self, direction: str) -> ActionResult:
        pyautogui = self._get_pyautogui()
        if direction == "previous":
            pyautogui.hotkey("alt", "shift", "tab")
        else:
            pyautogui.hotkey("alt", "tab")
        return ActionResult(True, f"Switched window: {direction}", ResponseStyle.switched_window(direction))

    def _open_target(self, target: str) -> ActionResult:
        spoken_target = self._normalize_target_name(target)
        resolved_target = self.memory.resolve(spoken_target) or spoken_target

        if resolved_target in self.settings.app_allowlist:
            app_target = self.settings.app_allowlist[resolved_target]
            self.memory.remember(spoken_target, resolved_target)
            self._launch_target(app_target, resolved_target)
            return ActionResult(
                True,
                f"Opened app: {resolved_target}",
                ResponseStyle.opening(resolved_target),
                opened_target=resolved_target,
            )

        if resolved_target in self.settings.site_allowlist:
            url = self.settings.site_allowlist[resolved_target]
            self.memory.remember(spoken_target, resolved_target)
            webbrowser.open(url)
            return ActionResult(
                True,
                f"Opened site: {resolved_target}",
                ResponseStyle.opening_site(resolved_target),
                opened_target=resolved_target,
            )

        if app_target := self._resolve_installed_app(resolved_target):
            self.memory.remember(spoken_target, resolved_target)
            self._launch_target(app_target, resolved_target)
            return ActionResult(
                True,
                f"Opened app: {resolved_target}",
                ResponseStyle.opening(resolved_target),
                opened_target=resolved_target,
            )

        if fuzzy_target := self._fuzzy_match_installed_app(resolved_target):
            app_target = self._resolve_installed_app(fuzzy_target)
            if app_target:
                self.memory.remember(spoken_target, fuzzy_target)
                self._launch_target(app_target, fuzzy_target)
                return ActionResult(
                    True,
                    f"Opened app: {fuzzy_target}",
                    f"Close enough. Opening {fuzzy_target}.",
                    opened_target=fuzzy_target,
                )

        return ActionResult(
            False,
            f"Target '{resolved_target}' could not be matched to an installed app or approved site.",
            f"I heard {resolved_target}, but I couldn't match it to an installed app or approved site.",
        )

    def _open_folder(self, target: str) -> ActionResult:
        folder = self.desktop.resolve_folder(target)
        if folder is None or not folder.exists():
            return ActionResult(
                False,
                f"Folder '{target}' could not be resolved.",
                f"I couldn't find a folder mapping for {target}.",
            )
        os.startfile(str(folder))  # type: ignore[attr-defined]
        folder_name = folder.name.lower() or "home"
        return ActionResult(
            True,
            f"Opened folder: {folder}",
            ResponseStyle.opening_folder(folder_name),
            opened_target=str(folder),
        )

    def _open_file(self, target: str) -> ActionResult:
        matches = self.desktop.search_file(target, limit=1)
        if not matches:
            return ActionResult(False, f"No local file matched '{target}'.", ResponseStyle.file_not_found(target))
        match = matches[0]
        os.startfile(str(match.path))  # type: ignore[attr-defined]
        return ActionResult(
            True,
            f"Opened file: {match.path}",
            ResponseStyle.opening_file(match.path.name),
            opened_target=str(match.path),
        )

    def _search_web(self, query: str) -> ActionResult:
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        return ActionResult(True, f"Searched web for: {query}", ResponseStyle.web_search(query))

    @staticmethod
    def _open_source(url: str, title: str) -> ActionResult:
        webbrowser.open(url)
        return ActionResult(True, f"Opened source: {title}", f"At once. Opening {title}.", opened_target=title)

    def _get_pyautogui(self):
        if self._pyautogui is None:
            import pyautogui

            pyautogui.FAILSAFE = True
            self._pyautogui = pyautogui
        return self._pyautogui

    @staticmethod
    def _get_clipboard_text() -> str:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            LOGGER.warning("Get-Clipboard failed: %s", result.stderr.strip())
            return ""
        return result.stdout.strip()

    @staticmethod
    def _clipboard_note_path() -> Path:
        return APP_DIR / "clipboard-notes.md"

    @classmethod
    def _focus_candidate_names(cls, target: str) -> list[str]:
        compact = target.replace(" ", "")
        candidates = [target, compact]
        if target == "visual studio code":
            candidates.extend(["code"])
        elif target == "calculator":
            candidates.extend(["calculator", "calc"])
        elif target == "chrome":
            candidates.extend(["chrome"])
        elif target == "notepad":
            candidates.extend(["notepad"])

        ordered: list[str] = []
        for item in candidates:
            lowered = item.lower()
            if lowered and lowered not in ordered:
                ordered.append(lowered)
        return ordered

    @staticmethod
    def _launch_target(target: str, spoken_name: str) -> None:
        if "://" in target or target.endswith(":"):
            os.startfile(target)  # type: ignore[attr-defined]
            return

        if os.path.isabs(target):
            if os.path.exists(target):
                subprocess.Popen([target], shell=False)
                return

            executable_name = os.path.splitext(os.path.basename(target))[0]
            if shutil.which(executable_name):
                subprocess.Popen([executable_name], shell=False)
                return

            if spoken_name == "chrome":
                os.startfile("https://www.google.com")  # type: ignore[attr-defined]
                return

            raise FileNotFoundError(f"Configured path does not exist: {target}")

        subprocess.Popen([target], shell=False)

    @staticmethod
    def _normalize_target_name(target: str) -> str:
        normalized = target.lower().strip()
        normalized = normalized.replace("'", "")
        normalized = normalized.replace("-", " ")
        for phrase in ("please", "for me", "right now"):
            normalized = normalized.replace(phrase, " ")
        tokens = [token for token in normalized.split() if token not in {"the", "a", "an", "up", "app"}]
        collapsed = " ".join(tokens).strip()
        aliases = {
            "calc": "calculator",
            "calculator": "calculator",
            "chrome": "chrome",
            "google chrome": "chrome",
            "browser": "chrome",
            "notepad": "notepad",
            "settings": "settings",
            "system settings": "settings",
            "vs code": "visual studio code",
            "vscode": "visual studio code",
            "visual studio code": "visual studio code",
            "vs good": "visual studio code",
            "of us could": "visual studio code",
            "or vs code": "visual studio code",
        }
        return aliases.get(collapsed, collapsed)

    def _resolve_installed_app(self, target: str) -> str | None:
        for candidate in self._candidate_executable_names(target):
            if path := shutil.which(candidate):
                return path
            if registered := self._find_registered_app_path(candidate):
                return registered

        if shortcut := self._find_start_menu_shortcut(target):
            return str(shortcut)
        return None

    def _fuzzy_match_installed_app(self, target: str) -> str | None:
        catalog = self._installed_app_catalog()
        if not catalog:
            return None
        matches = difflib.get_close_matches(target, catalog, n=1, cutoff=0.58)
        return matches[0] if matches else None

    @staticmethod
    def _candidate_executable_names(target: str) -> list[str]:
        compact = target.replace(" ", "")
        candidates = [
            compact,
            f"{compact}.exe",
            target.replace(" ", ""),
            target.replace(" ", "") + ".exe",
        ]
        special = {
            "visual studio code": ["code", "code.exe"],
            "calculator": ["calc", "calc.exe"],
            "settings": ["ms-settings:"],
            "notepad": ["notepad", "notepad.exe"],
            "chrome": ["chrome", "chrome.exe"],
        }
        ordered: list[str] = []
        for item in special.get(target, []) + candidates:
            if item not in ordered:
                ordered.append(item)
        return ordered

    def _installed_app_catalog(self) -> list[str]:
        names = set(self.settings.app_allowlist) | set(self.memory.snapshot())
        names.update({"calculator", "chrome", "notepad", "settings", "visual studio code"})

        shortcut_roots = [
            Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path.home() / "Desktop",
            Path.home() / r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        ]
        for root in shortcut_roots:
            if not root.exists():
                continue
            for shortcut in root.rglob("*.lnk"):
                names.add(self._normalize_target_name(shortcut.stem))
        return sorted(name for name in names if name)

    @staticmethod
    def _find_registered_app_path(candidate: str) -> str | None:
        subkey = candidate if candidate.endswith(".exe") else f"{candidate}.exe"
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{subkey}") as key:
                    value, _ = winreg.QueryValueEx(key, None)
                    if value and os.path.exists(value):
                        return value
            except OSError:
                continue
        return None

    @staticmethod
    def _find_start_menu_shortcut(target: str) -> Path | None:
        normalized_target = target.lower()
        shortcut_roots = [
            Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path.home() / "Desktop",
            Path.home() / r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        ]
        candidates: list[Path] = []
        for root in shortcut_roots:
            if not root.exists():
                continue
            for shortcut in root.rglob("*.lnk"):
                stem = shortcut.stem.lower()
                if normalized_target == stem or normalized_target in stem:
                    candidates.append(shortcut)
        if not candidates:
            return None
        candidates.sort(key=lambda path: (len(path.stem), path.stem))
        return candidates[0]

    @staticmethod
    def _normalize_expression(expression: str) -> str:
        normalized = expression.lower().strip()
        replacements = {
            "multiplied by": "*",
            "times": "*",
            "plus": "+",
            "minus": "-",
            "divided by": "/",
            "over": "/",
            "modulo": "%",
            "mod": "%",
            "power of": "**",
            "to the power of": "**",
        }
        for phrase, operator in replacements.items():
            normalized = normalized.replace(phrase, f" {operator} ")
        normalized = re.sub(r"(?<=\d)\s*x\s*(?=\d)", " * ", normalized)
        normalized = re.sub(r"\bon the calculator(?: app)?\b", "", normalized)
        normalized = re.sub(r"\bin calculator\b", "", normalized)
        normalized = normalized.replace(",", " ")
        normalized = " ".join(ActionExecutor._replace_number_words(normalized.split()))
        return normalized.removeprefix("what is ").removeprefix("whats ").strip()

    @classmethod
    def _safe_eval_expression(cls, expression: str) -> float:
        node = ast.parse(expression, mode="eval")
        return float(cls._eval_ast(node.body))

    @classmethod
    def _eval_ast(cls, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = cls._eval_ast(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)):
            left = cls._eval_ast(node.left)
            right = cls._eval_ast(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
            return left**right
        raise ValueError("Unsupported expression")

    @staticmethod
    def _format_number(value: float) -> str:
        if value.is_integer():
            return str(int(value))
        return f"{value:.6f}".rstrip("0").rstrip(".")

    @staticmethod
    def _replace_number_words(tokens: list[str]) -> list[str]:
        number_words = {
            "zero": "0",
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9",
            "ten": "10",
            "eleven": "11",
            "twelve": "12",
            "thirteen": "13",
            "fourteen": "14",
            "fifteen": "15",
            "sixteen": "16",
            "seventeen": "17",
            "eighteen": "18",
            "nineteen": "19",
            "twenty": "20",
        }
        return [number_words.get(token, token) for token in tokens]
