from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlotInfo:
    name: str
    description: str
    required: bool = True


@dataclass
class Capability:
    intent: str
    description: str
    slots: list[SlotInfo] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


class CapabilityRegistry:
    def __init__(self) -> None:
        self.capabilities: dict[str, Capability] = {}
        self._register_default_capabilities()

    def register(self, capability: Capability) -> None:
        self.capabilities[capability.intent] = capability

    def _register_default_capabilities(self) -> None:
        definitions = [
            ("set_timer", "Set or start a countdown timer.", [("duration", "Numeric duration."), ("unit", "second, minute, or hour.")], ["set a timer for 5 minutes"]),
            ("set_reminder", "Set a spoken reminder for a future time.", [("text", "Reminder text."), ("duration", "Numeric duration."), ("unit", "second, minute, or hour.")], ["remind me to call Mom in 2 hours"]),
            ("set_alarm", "Set a spoken alarm for a clock time.", [("hour", "Hour value."), ("minute", "Minute value."), ("period", "am, pm, or empty for 24-hour time.")], ["set an alarm for 7:30 am"]),
            ("add_task", "Add an item to the productivity task list.", [("task", "Task description.")], ["add buy groceries to my task list"]),
            ("list_tasks", "List the user's tasks.", [], ["list my tasks"]),
            ("clear_tasks", "Clear all tasks from the user's task list.", [], ["clear my task list"]),
            ("clear_timers", "Clear all active countdown timers.", [], ["clear my timers"]),
            ("clear_reminders", "Clear all active reminders.", [], ["clear my reminders"]),
            ("clear_alarms", "Clear all active alarms.", [], ["clear my alarms"]),
            ("take_note", "Append a quick note to the notes file.", [("text", "Note content.")], ["take a note to fix the script tomorrow"]),
            ("browser_summarize", "Extract and summarize the active browser page.", [], ["summarize this page"]),
            ("browser_tab_next", "Switch to the next browser tab.", [], ["next tab"]),
            ("browser_tab_prev", "Switch to the previous browser tab.", [], ["previous tab"]),
            ("browser_tab_new", "Open a new browser tab.", [], ["open a new tab"]),
            ("browser_tab_close", "Close the active browser tab.", [], ["close this tab"]),
            ("browser_back", "Navigate back in browser history.", [], ["go back"]),
            ("browser_forward", "Navigate forward in browser history.", [], ["go forward"]),
            ("browser_refresh", "Refresh the active browser page.", [], ["refresh this page"]),
            ("dictate", "Type text at the current cursor position.", [("text", "Exact text to type.")], ["type hello world"]),
            ("clipboard_copy", "Copy the current selection to the clipboard.", [], ["copy selection"]),
            ("clipboard_paste", "Paste clipboard contents at the current cursor.", [], ["paste clipboard contents"]),
            ("clipboard_read", "Read the current clipboard text aloud.", [], ["what is on my clipboard"]),
            ("clipboard_save_note", "Save clipboard text to a local note.", [], ["save clipboard to note"]),
            ("switch_window", "Switch to the next or previous desktop window.", [("direction", "next or previous.", False)], ["switch back"]),
            ("focus_target", "Focus a running application or window.", [("target", "Application name or window title.")], ["switch to notepad"]),
            ("calculate", "Evaluate a mathematical expression.", [("expression", "Raw mathematical expression.")], ["calculate 12 divided by 3"]),
            ("open_folder", "Open a system folder.", [("target", "Folder name such as downloads or documents.")], ["open downloads folder"]),
            ("open_file", "Search for and open a local file.", [("target", "Partial or full filename.")], ["open file budget report"]),
            ("open_target", "Launch an app or open an approved website.", [("target", "Application or website alias.")], ["open notepad"]),
            ("open_source", "Open a web source URL.", [("url", "Source URL."), ("title", "Optional source title.", False)], ["open source https://example.com"]),
            ("web_search", "Search the web.", [("query", "Search query.")], ["search the web for Python testing"]),
            ("recall_memory", "Retrieve and summarize local research archive material.", [("query", "Topic to retrieve.")], ["summarize Python testing"]),
            ("weather", "Get weather for a location.", [("location", "Location to check.", False)], ["weather in Beirut"]),
            ("qa", "Answer a general question or conversation prompt.", [("query", "Question or prompt.")], ["what is the capital of France"]),
            ("notepad_write_and_save", "Write text in Notepad and save it.", [("text", "Text to write."), ("filename", "Filename to save.")], ["write hello and save as notes.txt in notepad"]),
            ("browser_search_and_bookmark", "Search in the browser and bookmark the result.", [("query", "Search query.")], ["search for Python testing and bookmark it"]),
            ("vscode_open_terminal", "Open the terminal pane in Visual Studio Code.", [], ["open terminal in vscode"]),
            ("ui_click_coordinate", "Click at a screen coordinate.", [("x", "X coordinate."), ("y", "Y coordinate.")], ["click at 100 200"]),
            ("ui_double_click_coordinate", "Double click at a screen coordinate.", [("x", "X coordinate."), ("y", "Y coordinate.")], ["double click at 100 200"]),
            ("ui_write_at_coordinate", "Focus and type text at a screen coordinate.", [("x", "X coordinate."), ("y", "Y coordinate."), ("text", "Text to write.")], ["write hello at 100 200"]),
            ("ui_click_control", "Click a named accessibility control in a target window.", [("control_name", "Control name."), ("window_title", "Target window title.")], ["click Save in notepad"]),
            ("power_action", "Execute a system power command.", [("action", "shutdown, restart, or sleep.")], ["shutdown the system"]),
            ("delete_file", "Delete a local file.", [("target", "Filename to delete.")], ["delete notes.txt"]),
            ("send_email", "Draft and send an email message.", [("to", "Recipient email."), ("subject", "Email subject.", False), ("body", "Email body text.", False)], ["send email to john@example.com"]),
        ]

        for intent, description, slot_definitions, examples in definitions:
            self.register(
                Capability(
                    intent=intent,
                    description=description,
                    slots=[SlotInfo(*slot) for slot in slot_definitions],
                    examples=examples,
                )
            )

    def format_for_prompt(self) -> str:
        lines = [
            "Intent Routing Guidelines:",
            "You are responsible for routing user commands to structured intents.",
            "Analyze the user's input and match it to one capability below when possible.",
            "Return only valid JSON in this format:",
            '{"intent": "<intent_name>", "slots": {"<slot_key>": "<slot_value>"}}',
            "Route general questions to qa. Route unsupported commands to unsupported.",
            "",
            "Capabilities Registry:",
        ]
        for capability in self.capabilities.values():
            lines.append(f"- Intent: {capability.intent}")
            lines.append(f"  Description: {capability.description}")
            if capability.slots:
                lines.append("  Slots:")
                for slot in capability.slots:
                    requirement = "required" if slot.required else "optional"
                    lines.append(f"    - {slot.name}: {slot.description} ({requirement})")
            else:
                lines.append("  Slots: None")
            if capability.examples:
                examples = ", ".join(f'"{example}"' for example in capability.examples)
                lines.append(f"  Examples: {examples}")
            lines.append("")
        return "\n".join(lines)
