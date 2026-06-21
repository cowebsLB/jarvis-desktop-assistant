from __future__ import annotations

import logging
import time

from .models import ActionResult

LOGGER = logging.getLogger(__name__)


class UIController:
    def __init__(self, executor) -> None:
        self.executor = executor

    # ── Coordinate-based actions ─────────────────────────────────────────────

    def click_coordinate(self, x: int, y: int) -> ActionResult:
        try:
            pyautogui = self.executor._get_pyautogui()
            pyautogui.click(x, y)
            msg = f"Clicked coordinate ({x}, {y})."
            LOGGER.info(msg)
            return ActionResult(True, msg, msg)
        except Exception as e:
            msg = f"Failed to click coordinate ({x}, {y}): {e}"
            LOGGER.error(msg)
            return ActionResult(False, msg, "I failed to click at those coordinates.")

    def double_click_coordinate(self, x: int, y: int) -> ActionResult:
        try:
            pyautogui = self.executor._get_pyautogui()
            pyautogui.doubleClick(x, y)
            msg = f"Double-clicked coordinate ({x}, {y})."
            LOGGER.info(msg)
            return ActionResult(True, msg, msg)
        except Exception as e:
            msg = f"Failed to double-click coordinate ({x}, {y}): {e}"
            LOGGER.error(msg)
            return ActionResult(False, msg, "I failed to double click at those coordinates.")

    def write_to_coordinate(self, x: int, y: int, text: str) -> ActionResult:
        try:
            pyautogui = self.executor._get_pyautogui()
            pyautogui.click(x, y)
            time.sleep(0.2)
            pyautogui.write(text, interval=0.01)
            msg = f"Wrote '{text}' to coordinate ({x}, {y})."
            LOGGER.info(msg)
            return ActionResult(True, msg, f"Wrote text at coordinates {x} {y}.")
        except Exception as e:
            msg = f"Failed to write to coordinate ({x}, {y}): {e}"
            LOGGER.error(msg)
            return ActionResult(False, msg, "I failed to type at those coordinates.")

    # ── pywinauto-based window control actions ────────────────────────────────

    def click_control(self, window_title: str, control_name: str) -> ActionResult:
        try:
            focus_res = self.executor._focus_target(window_title)
            if not focus_res.success:
                return ActionResult(
                    False,
                    f"Could not find or focus window '{window_title}' to click control.",
                    f"I couldn't find a window named {window_title}.",
                )
            time.sleep(0.5)
            import pywinauto
            app = pywinauto.Application(backend="uia").connect(title_re=f".*{window_title}.*", timeout=3)
            window = app.window(title_re=f".*{window_title}.*")
            control = window.child_window(title=control_name)
            control.click_input()
            msg = f"Clicked control '{control_name}' in window '{window_title}'."
            LOGGER.info(msg)
            return ActionResult(True, msg, msg)
        except ImportError:
            msg = f"pywinauto not installed; cannot click control '{control_name}' in window '{window_title}'."
            LOGGER.warning(msg)
            return ActionResult(False, msg, "UI automation library pywinauto is not installed on this system.")
        except Exception as e:
            msg = f"Failed to click control '{control_name}' in window '{window_title}': {e}"
            LOGGER.error(msg)
            return ActionResult(False, msg, f"I could not click control {control_name} in window {window_title}.")

    def read_text_from_control(self, window_title: str, control_name: str) -> ActionResult:
        """Read the text value of a named accessibility control in a desktop window."""
        try:
            focus_res = self.executor._focus_target(window_title)
            if not focus_res.success:
                return ActionResult(
                    False,
                    f"Could not focus window '{window_title}'.",
                    f"I couldn't find a window named {window_title}.",
                )
            time.sleep(0.5)
            import pywinauto
            app = pywinauto.Application(backend="uia").connect(title_re=f".*{window_title}.*", timeout=3)
            window = app.window(title_re=f".*{window_title}.*")
            control = window.child_window(title=control_name, timeout=2)
            text = control.get_value() if hasattr(control, "get_value") else control.window_text()
            text = (text or "").strip()
            if not text:
                return ActionResult(False, f"Control '{control_name}' is empty.", f"The {control_name} field is empty.")
            msg = f"Read '{text}' from control '{control_name}' in '{window_title}'."
            LOGGER.info(msg)
            return ActionResult(True, msg, text)
        except ImportError:
            return ActionResult(False, "pywinauto not installed.", "UI automation library is not installed.")
        except Exception as e:
            msg = f"Failed to read control '{control_name}' in '{window_title}': {e}"
            LOGGER.error(msg)
            return ActionResult(False, msg, f"I could not read {control_name} from {window_title}.")

    def set_text_in_control(self, window_title: str, control_name: str, text: str) -> ActionResult:
        """Clear and type text into a named accessibility control in a desktop window."""
        try:
            focus_res = self.executor._focus_target(window_title)
            if not focus_res.success:
                return ActionResult(
                    False,
                    f"Could not focus window '{window_title}'.",
                    f"I couldn't find a window named {window_title}.",
                )
            time.sleep(0.5)
            import pywinauto
            app = pywinauto.Application(backend="uia").connect(title_re=f".*{window_title}.*", timeout=3)
            window = app.window(title_re=f".*{window_title}.*")
            control = window.child_window(title=control_name, timeout=2)
            control.click_input()
            time.sleep(0.2)
            # Clear existing text
            pyautogui = self.executor._get_pyautogui()
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("backspace")
            time.sleep(0.1)
            pyautogui.write(text, interval=0.01)
            msg = f"Set '{text}' in control '{control_name}' in '{window_title}'."
            LOGGER.info(msg)
            return ActionResult(True, msg, f"Typed {text} into {control_name}.")
        except ImportError:
            return ActionResult(False, "pywinauto not installed.", "UI automation library is not installed.")
        except Exception as e:
            msg = f"Failed to set text in control '{control_name}' in '{window_title}': {e}"
            LOGGER.error(msg)
            return ActionResult(False, msg, f"I could not type into {control_name} in {window_title}.")

    def get_window_info(self, window_title: str) -> ActionResult:
        """Return a summary of the top-level controls in a window (titles and control types)."""
        try:
            focus_res = self.executor._focus_target(window_title)
            if not focus_res.success:
                return ActionResult(
                    False,
                    f"Could not focus window '{window_title}'.",
                    f"I couldn't find a window named {window_title}.",
                )
            time.sleep(0.5)
            import pywinauto
            app = pywinauto.Application(backend="uia").connect(title_re=f".*{window_title}.*", timeout=3)
            window = app.window(title_re=f".*{window_title}.*")
            children = window.children()
            items = []
            for child in children[:20]:  # cap at 20 to keep response readable
                try:
                    title = child.window_text().strip()
                    ctrl_type = child.element_info.control_type or "Unknown"
                    if title:
                        items.append(f"{ctrl_type}: {title}")
                except Exception:
                    continue
            if not items:
                summary = f"Window '{window_title}' has no labelled controls."
            else:
                summary = f"Controls in '{window_title}': " + "; ".join(items)
            LOGGER.info(summary)
            return ActionResult(True, summary, summary)
        except ImportError:
            return ActionResult(False, "pywinauto not installed.", "UI automation library is not installed.")
        except Exception as e:
            msg = f"Failed to inspect window '{window_title}': {e}"
            LOGGER.error(msg)
            return ActionResult(False, msg, f"I could not inspect the {window_title} window.")

    def scroll_in_window(self, window_title: str, direction: str, amount: int = 3) -> ActionResult:
        """Scroll up or down inside a window using mouse wheel."""
        try:
            focus_res = self.executor._focus_target(window_title)
            if not focus_res.success:
                return ActionResult(
                    False,
                    f"Could not focus window '{window_title}'.",
                    f"I couldn't find a window named {window_title}.",
                )
            time.sleep(0.3)
            pyautogui = self.executor._get_pyautogui()
            clicks = amount if direction == "down" else -amount
            pyautogui.scroll(clicks=clicks)
            msg = f"Scrolled {direction} {amount} ticks in '{window_title}'."
            LOGGER.info(msg)
            return ActionResult(True, msg, f"Scrolled {direction} in {window_title}.")
        except Exception as e:
            msg = f"Failed to scroll in '{window_title}': {e}"
            LOGGER.error(msg)
            return ActionResult(False, msg, f"I couldn't scroll in {window_title}.")
