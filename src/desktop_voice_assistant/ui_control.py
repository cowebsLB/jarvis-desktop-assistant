from __future__ import annotations

import logging
import time

from .models import ActionResult

LOGGER = logging.getLogger(__name__)


class UIController:
    def __init__(self, executor) -> None:
        self.executor = executor

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

    def click_control(self, window_title: str, control_name: str) -> ActionResult:
        try:
            # Attempt focusing the target window first
            focus_res = self.executor._focus_target(window_title)
            if not focus_res.success:
                return ActionResult(False, f"Could not find or focus window '{window_title}' to click control.", f"I couldn't find a window named {window_title}.")

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
