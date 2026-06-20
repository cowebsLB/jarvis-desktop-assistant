from desktop_voice_assistant.intent_router import IntentRouter


def test_route_dictation() -> None:
    result = IntentRouter().route("Type hello world")
    assert result.intent == "dictate"
    assert result.slots["text"] == "hello world"


def test_route_dictation_with_extra_words() -> None:
    result = IntentRouter().route("Hey Jarvis, can you please type hello world for me")
    assert result.intent == "dictate"
    assert result.slots["text"] == "hello world"


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
