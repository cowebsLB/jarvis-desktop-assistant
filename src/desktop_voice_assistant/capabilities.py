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
        # set_timer
        self.register(Capability(
            intent="set_timer",
            description="Set or start a countdown timer for a specific duration.",
            slots=[
                SlotInfo("duration", "Numeric value of the duration (e.g. '5', '10') as a string."),
                SlotInfo("unit", "Unit of duration, restricted to: second, sec, minute, min, hour, hr.")
            ],
            examples=["set a timer for 5 minutes", "timer for 10 seconds", "start a timer for 1 hour"]
        ))

        # set_reminder
        self.register(Capability(
            intent="set_reminder",
            description="Set a spoken reminder for a task in the future.",
            slots=[
                SlotInfo("text", "Description of what to remind about (e.g. 'check the oven')."),
                SlotInfo("duration", "Numeric value of the duration before reminder triggers."),
                SlotInfo("unit", "Unit of duration, restricted to: second, sec, minute, min, hour, hr.")
            ],
            examples=["remind me to lock the door in 20 minutes", "set a reminder to call Mom in 2 hours"]
        ))

        # set_alarm
        self.register(Capability(
            intent="set_alarm",
            description="Set a spoken alarm for a specific clock time of day.",
            slots=[
                SlotInfo("hour", "Hour value (1-12 or 0-23) as a string."),
                SlotInfo("minute", "Minute value (00-59) as a string. Default is '00' if not specified."),
                SlotInfo("period", "Time period, either 'am', 'pm', or empty if using 24-hour clock.")
            ],
            examples=["set an alarm for 7:30 am", "set an alarm for 8 pm", "alarm for 15:00"]
        ))

        # add_task
        self.register(Capability(
            intent="add_task",
            description="Add a new task or item to the user's productivity task list.",
            slots=[
                SlotInfo("task", "Description of the task to add.")
            ],
            examples=["add buy groceries to my task list", "add finish the report to my tasks"]
        ))

        # list_tasks
        self.register(Capability(
            intent="list_tasks",
            description="Display or show all tasks in the user's task list.",
            slots=[],
            examples=["list my tasks", "show my task list", "what are my tasks"]
        ))

        # clear_tasks
        self.register(Capability(
            intent="clear_tasks",
            description="Delete, empty, or clear all tasks from the user's task list.",
            slots=[],
            examples=["clear my task list", "delete all tasks", "empty my tasks"]
        ))

        # clear_timers
        self.register(Capability(
            intent="clear_timers",
            description="Clear or cancel all active countdown timers.",
            slots=[],
            examples=["clear my timers", "remove all timers", "cancel timers"]
        ))

        # clear_reminders
        self.register(Capability(
            intent="clear_reminders",
            description="Clear or cancel all active spoken task reminders.",
            slots=[],
            examples=["clear my reminders", "remove all reminders", "cancel reminders"]
        ))

        # clear_alarms
        self.register(Capability(
            intent="clear_alarms",
            description="Clear or cancel all active clock alarms.",
            slots=[],
            examples=["clear my alarms", "remove all alarms", "cancel alarms"]
        ))

        # take_note
        self.register(Capability(
            intent="take_note",
            description="Take a quick note and append it to the user's quick notes file.",
            slots=[
                SlotInfo("text", "Content of the note to save.")
            ],
            examples=["take a note that we need to fix the script tomorrow", "save note buy milk"]
        ))

        # browser_summarize
        self.register(Capability(
            intent="browser_summarize",
            description="Extract text content of the active web browser tab and summarize it.",
            slots=[],
            examples=["summarize this page", "explain the website", "summarize the active page"]
        ))

        # browser_tab_next
        self.register(Capability(
            intent="browser_tab_next",
            description="Switch focus to the next open tab in the active browser window.",
            slots=[],
            examples=["switch to the next tab", "next tab"]
        ))

        # browser_tab_prev
        self.register(Capability(
            intent="browser_tab_prev",
            description="Switch focus to the previous open tab in the active browser window.",
            slots=[],
            examples=["switch to the previous tab", "previous tab", "last tab"]
        ))

        # browser_tab_new
        self.register(Capability(
            intent="browser_tab_new",
            description="Open a new tab in the active web browser.",
            slots=[],
            examples=["open a new tab", "new tab"]
        ))

        # browser_tab_close
        self.register(Capability(
            intent="browser_tab_close",
            description="Close the currently active tab in the browser.",
            slots=[],
            examples=["close this tab", "close tab"]
        ))

        # browser_back
        self.register(Capability(
            intent="browser_back",
            description="Go back to the previous page in the web browser history.",
            slots=[],
            examples=["go back in history", "go back"]
        ))

        # browser_forward
        self.register(Capability(
            intent="browser_forward",
            description="Go forward to the next page in the web browser history.",
            slots=[],
            examples=["go forward in history", "go forward"]
        ))

        # browser_refresh
        self.register(Capability(
            intent="browser_refresh",
            description="Refresh or reload the active web page.",
            slots=[],
            examples=["refresh this page", "reload the tab"]
        ))

        # dictate
        self.register(Capability(
            intent="dictate",
            description="Type a specific text string at the current text cursor position.",
            slots=[
                SlotInfo("text", "The exact text to type.")
            ],
            examples=["type hello world", "dictate thank you very much"]
        ))

        # clipboard_copy
        self.register(Capability(
            intent="clipboard_copy",
            description="Copy the current selection to the clipboard using ctrl+c.",
            slots=[],
            examples=["copy selection", "copy this text"]
        ))

        # clipboard_paste
        self.register(Capability(
            intent="clipboard_paste",
            description="Paste text from the clipboard to the current cursor position.",
            slots=[],
            examples=["paste that", "paste clipboard contents"]
        ))

        # clipboard_read
        self.register(Capability(
            intent="clipboard_read",
            description="Read aloud whatever text is currently stored in the clipboard.",
            slots=[],
            examples=["read my clipboard", "what's on my clipboard"]
        ))

        # clipboard_save_note
        self.register(Capability(
            intent="clipboard_save_note",
            description="Save the text currently in the clipboard as a new note in notes.",
            slots=[],
            examples=["save clipboard to note", "save clipboard as note"]
        ))

        # switch_window
        self.register(Capability(
            intent="switch_window",
            description="Switch to the next or previous active window on the desktop.",
            slots=[
                SlotInfo("direction", "Either 'next' or 'previous'. Default is 'next'.")
            ],
            examples=["switch window", "focus previous window", "switch back"]
        ))

        # focus_target
        self.register(Capability(
            intent="focus_target",
            description="Bring a running application or window to the foreground and focus it.",
            slots=[
                SlotInfo("target", "The name of the target application or window title to focus.")
            ],
            examples=["focus on notepad", "switch to chrome", "bring up visual studio code"]
        ))

        # calculate
        self.register(Capability(
            intent="calculate",
            description="Evaluate a mathematical expression mathematically.",
            slots=[
                SlotInfo("expression", "The raw mathematical expression to evaluate (e.g. '12 divided by 3', '9 plus 10').")
            ],
            examples=["calculate 12 divided by 3", "what is 5 times 10"]
        ))

        # open_folder
        self.register(Capability(
            intent="open_folder",
            description="Open a system folder on the computer.",
            slots=[
                SlotInfo("target", "Folder to open (e.g., downloads, documents, desktop, home).")
            ],
            examples=["open downloads folder", "show my desktop folder"]
        ))

        # open_file
        self.register(Capability(
            intent="open_file",
            description="Search for and open a local file on the disk by name.",
            slots=[
                SlotInfo("target", "The partial or full filename to search and open.")
            ],
            examples=["open file budget report", "open document resume"]
        ))

        # open_target
        self.register(Capability(
            intent="open_target",
            description="Launch an installed program/app or open an approved website URL.",
            slots=[
                SlotInfo("target", "The name of the application or website alias (e.g., chrome, youtube, notepad).")
            ],
            examples=["open notepad", "launch youtube", "go to google"]
        ))

        # open_source
        self.register(Capability(
            intent="open_source",
            description="Open a web source url in the browser.",
            slots=[
                SlotInfo("url", "The URL of the source to open."),
                SlotInfo("title", "The optional title of the source to open.", required=False)
            ],
            examples=["open source https://example.com"]
        ))

        # web_search
        self.register(Capability(
            intent="web_search",
            description="Perform a web search using a search engine.",
            slots=[
                SlotInfo("query", "The search query string to look up.")
            ],
            examples=["search the web for weather in Beirut", "google who won the game"]
        ))

        # recall_memory
        self.register(Capability(
            intent="recall_memory",
            description="Retrieve and summarize information from the local research archive.",
            slots=[
                SlotInfo("query", "The topic or query to summarize from stored research.")
            ],
            examples=["summarize Python testing", "what do we know about quantum computing"]
        ))

        # weather
        self.register(Capability(
            intent="weather",
            description="Get the weather forecast for a specified city or country.",
            slots=[
                SlotInfo("location", "The location to check weather for. Can be empty for current location.")
            ],
            examples=["weather in lebanon", "what's the weather today"]
        ))

        # qa
        self.register(Capability(
            intent="qa",
            description="Ask a general knowledge question or follow-up question when no other desktop intent matches.",
            slots=[
                SlotInfo("query", "The text of the question or prompt.")
            ],
            examples=["what is the capital of France", "tell me the capital of Lebanon"]
        ))

        # notepad_write_and_save
        self.register(Capability(
            intent="notepad_write_and_save",
            description="Write content in Notepad and save it to a file.",
            slots=[
                SlotInfo("text", "The text content to write."),
                SlotInfo("filename", "The filename to save the text to.")
            ],
            examples=["write hello world and save as notes.txt in notepad", "write text and save as file.txt in notepad"]
        ))

        # browser_search_and_bookmark
        self.register(Capability(
            intent="browser_search_and_bookmark",
            description="Search for a query in the browser and bookmark the page.",
            slots=[
                SlotInfo("query", "The search query string to look up and bookmark.")
            ],
            examples=["search for python testing and bookmark it", "search browser for book reviews and bookmark"]
        ))

        # vscode_open_terminal
        self.register(Capability(
            intent="vscode_open_terminal",
            description="Open the terminal pane in Visual Studio Code.",
            slots=[],
            examples=["open terminal in vscode", "open vscode terminal"]
        ))

        # ui_click_coordinate
        self.register(Capability(
            intent="ui_click_coordinate",
            description="Click at specified screen coordinate coordinates (x, y).",
            slots=[
                SlotInfo("x", "The X coordinate value as a string."),
                SlotInfo("y", "The Y coordinate value as a string.")
            ],
            examples=["click at 100 200", "click coordinate 300 400"]
        ))

        # ui_double_click_coordinate
        self.register(Capability(
            intent="ui_double_click_coordinate",
            description="Double click at specified screen coordinate coordinates (x, y).",
            slots=[
                SlotInfo("x", "The X coordinate value as a string."),
                SlotInfo("y", "The Y coordinate value as a string.")
            ],
            examples=["double click at 100 200", "double click coordinate 300 400"]
        ))

        # ui_write_at_coordinate
        self.register(Capability(
            intent="ui_write_at_coordinate",
            description="Focus and write text at specified screen coordinate coordinates (x, y).",
            slots=[
                SlotInfo("x", "The X coordinate value as a string."),
                SlotInfo("y", "The Y coordinate value as a string."),
                SlotInfo("text", "The text content to write.")
            ],
            examples=["write hello world at 100 200", "type login details at 50 100"]
        ))

        # ui_click_control
        self.register(Capability(
            intent="ui_click_control",
            description="Click a named window control in a target application window.",
            slots=[
                SlotInfo("control_name", "The name of the button or control to click."),
                SlotInfo("window_title", "The title of the target application window.")
            ],
            examples=["click button Save in notepad", "click File in chrome"]
        ))

    def format_for_prompt(self) -> str:
        lines = [
            "Intent Routing Guidelines:",
            "You are also responsible for routing user commands to structured intents.",
            "Analyze the user's input and see if it matches any of the capabilities listed below.",
            "If it matches, you must return a valid JSON object matching this structure exactly (with NO other text, markdown formatting, or explanations):",
            "{\"intent\": \"<intent_name>\", \"slots\": {<slot_key>: <slot_value>}}",
            "",
            "If the request does not match any specific desktop intent, or if it is a general knowledge question, route it to either 'qa' (general questions/conversations) or 'unsupported' (commands we cannot fulfill).",
            "",
            "Capabilities Registry:"
        ]
        for cap in self.capabilities.values():
            lines.append(f"- Intent: {cap.intent}")
            lines.append(f"  Description: {cap.description}")
            if cap.slots:
                lines.append("  Slots:")
                for slot in cap.slots:
                    req_str = "required" if slot.required else "optional"
                    lines.append(f"    - {slot.name}: {slot.description} ({req_str})")
            else:
                lines.append("  Slots: None")
            if cap.examples:
                lines.append(f"  Examples: {', '.join(f'\"{ex}\"' for ex in cap.examples)}")
            lines.append("")
        return "\n".join(lines)
