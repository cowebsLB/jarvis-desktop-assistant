from desktop_voice_assistant.intent_router import IntentRouter


def test_route_dictation() -> None:
    result = IntentRouter().route("Type hello world")
    assert result.intent == "dictate"
    assert result.slots["text"] == "hello world"


def test_route_dictation_with_extra_words() -> None:
    result = IntentRouter().route("Hey Jarvis, can you please type hello world for me")
    assert result.intent == "dictate"
    assert result.slots["text"] == "hello world"


def test_route_clipboard_copy() -> None:
    result = IntentRouter().route("Copy selection")
    assert result.intent == "clipboard_copy"


def test_route_clipboard_paste() -> None:
    result = IntentRouter().route("Paste clipboard")
    assert result.intent == "clipboard_paste"


def test_route_clipboard_read() -> None:
    result = IntentRouter().route("What's on my clipboard")
    assert result.intent == "clipboard_read"


def test_route_clipboard_save_note() -> None:
    result = IntentRouter().route("Save clipboard to note")
    assert result.intent == "clipboard_save_note"


def test_route_focus_target() -> None:
    result = IntentRouter().route("Switch to notepad")
    assert result.intent == "focus_target"
    assert result.slots["target"] == "notepad"


def test_route_focus_target_with_focus_phrase() -> None:
    result = IntentRouter().route("Focus on chrome")
    assert result.intent == "focus_target"
    assert result.slots["target"] == "chrome"


def test_route_switch_window_next() -> None:
    result = IntentRouter().route("Switch window")
    assert result.intent == "switch_window"
    assert result.slots["direction"] == "next"


def test_route_switch_window_previous() -> None:
    result = IntentRouter().route("Switch back")
    assert result.intent == "switch_window"
    assert result.slots["direction"] == "previous"


def test_route_open_target() -> None:
    result = IntentRouter().route("Open notepad")
    assert result.intent == "open_target"
    assert result.slots["target"] == "notepad"


def test_route_open_target_with_preamble() -> None:
    result = IntentRouter().route("Hey Jarvis, could you open notepad please")
    assert result.intent == "open_target"
    assert result.slots["target"] == "notepad"


def test_route_open_target_with_visit_phrase() -> None:
    result = IntentRouter().route("Visit youtube")
    assert result.intent == "open_target"
    assert result.slots["target"] == "youtube"


def test_route_open_folder() -> None:
    result = IntentRouter().route("Open downloads folder")
    assert result.intent == "open_folder"
    assert result.slots["target"] == "downloads"


def test_route_open_file() -> None:
    result = IntentRouter().route("Open file budget report")
    assert result.intent == "open_file"
    assert result.slots["target"] == "budget report"


def test_route_calculate_expression() -> None:
    result = IntentRouter().route("Calculate 12 divided by 3")
    assert result.intent == "calculate"
    assert result.slots["expression"] == "12 divided by 3"


def test_route_what_is_math_to_calculate() -> None:
    result = IntentRouter().route("What is 9 plus 10")
    assert result.intent == "calculate"
    assert result.slots["expression"] == "9 plus 10"


def test_route_web_search() -> None:
    result = IntentRouter().route("Search the web for weather in Beirut")
    assert result.intent == "web_search"
    assert result.slots["query"] == "weather in beirut"


def test_route_recall_memory() -> None:
    result = IntentRouter().route("Summarize Python testing")
    assert result.intent == "recall_memory"
    assert result.slots["query"] == "python testing"


def test_route_qa() -> None:
    result = IntentRouter().route("What is the capital of France")
    assert result.intent == "qa"


def test_route_weather_request_to_web_search() -> None:
    result = IntentRouter().route("Hey Jarvis, can you check today's weather in Lebanon for me")
    assert result.intent == "weather"
    assert result.slots["location"] == "Lebanon"


def test_route_natural_question_to_qa() -> None:
    result = IntentRouter().route("Tell me the capital of Lebanon")
    assert result.intent == "qa"


def test_route_natural_question_with_preamble_to_qa() -> None:
    result = IntentRouter().route("Hey Jarvis, could you tell me the capital of Lebanon")
    assert result.intent == "qa"


def test_route_weather_request_without_location() -> None:
    result = IntentRouter().route("What's the weather today")
    assert result.intent == "weather"
    assert result.slots["location"] == ""


def test_route_unsupported() -> None:
    result = IntentRouter().route("Delete my downloads folder")
    assert result.intent == "unsupported"


def test_normalize_for_followup() -> None:
    normalized = IntentRouter().normalize_for_followup("Hey Jarvis, please open it for me")
    assert normalized == "open it"


def test_route_clear_timers() -> None:
    result = IntentRouter().route("Remove all timers")
    assert result.intent == "clear_timers"


def test_route_clear_reminders() -> None:
    result = IntentRouter().route("Cancel reminders")
    assert result.intent == "clear_reminders"


def test_route_clear_alarms() -> None:
    result = IntentRouter().route("delete all alarms")
    assert result.intent == "clear_alarms"


def test_route_open_with_question_mark() -> None:
    result = IntentRouter().route("Can you open VS Code?")
    assert result.intent == "open_target"
    assert result.slots["target"] == "vs code"


def test_route_timer_cancel_instead_of_set() -> None:
    result = IntentRouter().route("Can you remove the timer for 10 minutes?")
    assert result.intent == "clear_timers"


def test_route_notepad_write_and_save() -> None:
    result = IntentRouter().route("write hello world and save as notes.txt in notepad")
    assert result.intent == "notepad_write_and_save"
    assert result.slots["text"] == "hello world"
    assert result.slots["filename"] == "notes txt"

    result = IntentRouter().route("write log entries in notepad and save as work.log")
    assert result.intent == "notepad_write_and_save"
    assert result.slots["text"] == "log entries"
    assert result.slots["filename"] == "work log"

    result = IntentRouter().route("open notepad and type hello word in it")
    assert result.intent == "notepad_write_and_save"
    assert result.slots["text"] == "hello word"
    assert result.slots["filename"] == "notes.txt"

    result = IntentRouter().route("type hello word in notepad")
    assert result.intent == "notepad_write_and_save"
    assert result.slots["text"] == "hello word"
    assert result.slots["filename"] == "notes.txt"


def test_route_browser_search_and_bookmark() -> None:
    result = IntentRouter().route("search for python testing and bookmark it")
    assert result.intent == "browser_search_and_bookmark"
    assert result.slots["query"] == "python testing"

    result = IntentRouter().route("search browser for book reviews and bookmark")
    assert result.intent == "browser_search_and_bookmark"
    assert result.slots["query"] == "book reviews"


def test_route_vscode_open_terminal() -> None:
    result = IntentRouter().route("open terminal in vscode")
    assert result.intent == "vscode_open_terminal"

    result = IntentRouter().route("open vscode terminal")
    assert result.intent == "vscode_open_terminal"


def test_route_ui_click_coordinate() -> None:
    result = IntentRouter().route("click at 100 200")
    assert result.intent == "ui_click_coordinate"
    assert result.slots["x"] == "100"
    assert result.slots["y"] == "200"

    result = IntentRouter().route("click coordinate 350, 420")
    assert result.intent == "ui_click_coordinate"
    assert result.slots["x"] == "350"
    assert result.slots["y"] == "420"


def test_route_ui_double_click_coordinate() -> None:
    result = IntentRouter().route("double click at 100 200")
    assert result.intent == "ui_double_click_coordinate"
    assert result.slots["x"] == "100"
    assert result.slots["y"] == "200"


def test_route_ui_write_at_coordinate() -> None:
    result = IntentRouter().route("write hello world at 100 200")
    assert result.intent == "ui_write_at_coordinate"
    assert result.slots["text"] == "hello world"
    assert result.slots["x"] == "100"
    assert result.slots["y"] == "200"


def test_route_ui_click_control() -> None:
    result = IntentRouter().route("click button Save in notepad")
    assert result.intent == "ui_click_control"
    assert result.slots["control_name"] == "save"
    assert result.slots["window_title"] == "notepad"


def test_route_spotify_play_pause() -> None:
    router = IntentRouter()
    for phrase in ("pause spotify", "resume music", "pause music", "play pause"):
        result = router.route(phrase)
        assert result.intent == "spotify_play_pause", f"Expected spotify_play_pause for '{phrase}'"


def test_route_spotify_next_track() -> None:
    router = IntentRouter()
    for phrase in ("next song", "next track", "skip track"):
        result = router.route(phrase)
        assert result.intent == "spotify_next_track", f"Expected spotify_next_track for '{phrase}'"


def test_route_spotify_prev_track() -> None:
    router = IntentRouter()
    for phrase in ("previous song", "previous track", "last song"):
        result = router.route(phrase)
        assert result.intent == "spotify_prev_track", f"Expected spotify_prev_track for '{phrase}'"


def test_route_spotify_volume() -> None:
    router = IntentRouter()
    assert router.route("volume up").intent == "spotify_volume_up"
    assert router.route("louder").intent == "spotify_volume_up"
    assert router.route("volume down").intent == "spotify_volume_down"
    assert router.route("quieter").intent == "spotify_volume_down"


def test_route_discord_mute() -> None:
    router = IntentRouter()
    for phrase in ("mute discord", "unmute discord", "discord mute", "toggle mute"):
        result = router.route(phrase)
        assert result.intent == "discord_mute", f"Expected discord_mute for '{phrase}'"


def test_route_discord_deafen() -> None:
    router = IntentRouter()
    for phrase in ("deafen discord", "undeafen discord"):
        result = router.route(phrase)
        assert result.intent == "discord_deafen", f"Expected discord_deafen for '{phrase}'"


def test_route_discord_navigate() -> None:
    result = IntentRouter().route("go to discord channel general")
    assert result.intent == "discord_navigate"
    assert "general" in result.slots["target"]


def test_route_slack_mute() -> None:
    router = IntentRouter()
    for phrase in ("mute slack", "unmute slack", "slack mute"):
        result = router.route(phrase)
        assert result.intent == "slack_mute", f"Expected slack_mute for '{phrase}'"


def test_route_slack_navigate() -> None:
    result = IntentRouter().route("go to slack channel engineering")
    assert result.intent == "slack_navigate"
    assert "engineering" in result.slots["target"]


def test_route_browser_click_control() -> None:
    result = IntentRouter().route("click the Sign In button on the browser")
    assert result.intent == "browser_click_control"
    assert "sign in" in result.slots["control_name"]


def test_route_browser_fill_form() -> None:
    result = IntentRouter().route("fill the form username: myuser in the browser")
    assert result.intent == "browser_fill_form"
