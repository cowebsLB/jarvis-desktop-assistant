# Features

## Implemented

### Wake Word

- Supported wake word: `hey jarvis`
- Runs locally using `openwakeword`
- Uses ONNX runtime
- Only one request is allowed at a time
- Wake listener pauses during active request handling
- Audible listen cue plays when command capture starts

### Speech to Text

- Local transcription using `faster-whisper`
- Default STT model: `base.en`
- CPU-first runtime with configurable compute type
- Adaptive end-of-speech detection
- Configurable capture behavior:
  - maximum request length
  - minimum capture length
  - silence timeout
  - speech threshold

### Text to Speech

- Local offline TTS using `pyttsx3`
- Prefers a more natural installed Windows voice such as `Zira` when available
- Spoken phrasing is customized toward a Stark-house butler-tech tone instead of flat stock confirmations
- Spoken confirmations and spoken weather/QA responses supported

### Intent Routing

- `dictate`
- `clipboard_copy`
- `clipboard_paste`
- `clipboard_read`
- `clipboard_save_note`
- `calculate`
- `focus_target`
- `switch_window`
- `open_target`
- `open_folder`
- `open_file`
- `web_search`
- `recall_memory`
- `weather`
- `qa`
- `notepad_write_and_save`
- `browser_search_and_bookmark`
- `vscode_open_terminal`
- `ui_click_coordinate`
- `ui_double_click_coordinate`
- `ui_write_at_coordinate`
- `ui_click_control`
- `unsupported`

### Natural Language Tolerance

Current normalization handles:

- wake-word leftovers like `hey jarvis`
- polite wrappers like `can you`, `could you`, `please`
- filler endings like `for me`, `right now`
- extra articles in app names like `the calculator`

### Failure Feedback

- If no usable speech is captured, Jarvis now gives a retry hint with example commands
- If a request is unsupported, Jarvis now says what it heard and suggests the closest supported path when possible
- Current targeted feedback covers:
  - likely app-launch requests
  - search phrasing
  - unsupported command shapes outside the current desktop-control set

### Desktop Actions

- type text into the active window
- copy the current selection with `Ctrl+C`
- paste clipboard contents with `Ctrl+V`
- read current clipboard text back aloud
- save current clipboard text to a local note file
- calculate local arithmetic expressions with spoken results
- focus a visible app window by name or title
- switch to the next or previous desktop window
- open allowlisted apps
- open many installed apps even when they are not in the explicit allowlist
- app discovery currently uses:
  - PATH executable lookup
  - Windows App Paths registry entries
  - Start Menu and desktop shortcuts
- adaptive app-name memory stores learned spoken aliases for future launches
- open common user folders:
  - Desktop
  - Documents
  - Downloads
  - Music
  - Pictures
  - Videos
  - Home
- search local files by name across common user folders and the current working directory
- open the best local file match directly when one is found
- open allowlisted websites
- browser/site opening also responds to broader phrases such as:
  - `launch`
  - `start`
  - `go to`
  - `visit`
- browser opening still works when explicitly needed
- clipboard notes are stored under `%USERPROFILE%\.desktop_voice_assistant\clipboard-notes.md`

### Direct Web Research

- web search no longer has to open the browser
- Jarvis now:
  - searches the web internally
  - fetches and scrapes source pages
  - summarizes the findings aloud
  - stores the material locally for later recall
- research answers append a brief offer to open sources if needed
- live answers now add caution when:
  - evidence is limited
  - live sources appear to conflict

### Local Research Archive

- stored in local SQLite
- keeps fetched pages, snippets, summaries, original queries, and timestamps
- can answer later follow-up questions from stored notes
- supports recall prompts like `summarize python testing`
- stores local embeddings for semantic recall when the embedding model is available
- stored hits now expose freshness metadata so older notes can be marked stale in recall
- semantic retrieval now degrades explicitly to keyword-only mode when embeddings are unavailable

### Weather

- live weather by place name
- default fallback location: `Beirut, Lebanon`
- spoken summary includes:
  - current temperature
  - high / low
  - rain chance

### Local QA

- local question answering through Ollama
- currently configured local model:
  - `qwen2.5-coder:1.5B`
- archived research is now used as extra context when relevant so the smaller model answers from evidence instead of memory alone
- semantic archive recall lets follow-up phrasing drift without depending on exact keyword matches

### Follow-Up Context

- short-lived session context is now tracked across consecutive requests
- supported follow-up patterns currently include:
  - `summarize that`
  - `search again`
  - `search again but for today`
  - `open it`
- follow-up context can reuse:
  - the last research query
  - the first source from the last research result
  - the last opened target
- follow-up context expires after a configurable timeout

### Clarification And Confirmation

- ambiguous follow-up commands now ask for missing context instead of guessing
- current clarification coverage includes:
  - `open it`
  - `open that`
  - `summarize that`
- fuzzy app-name recovery now asks for confirmation before launch
- destructive actions (such as clearing tasks, timers, reminders, and alarms) now prompt for explicit user confirmation before executing
- confirmation responses currently supported:
  - `yes`
  - `yeah`
  - `yep`
  - `confirm`
  - `do it`
  - `go ahead`
  - `no`
  - `nope`
  - `cancel`
  - `stop`
- approved confirmations execute the pending action on the next turn
- rejected confirmations clear the pending action without side effects

### Tray App

- tray process stays alive in background
- manual `Listen now`
- `Warm speech model`
- wake-word enable/disable
- open settings file
- quit
- tray title now reflects assistant runtime state instead of a loose ad-hoc label

### Floating HUD

- first-pass floating HUD is now available as an always-on-top orb
- HUD behavior currently includes:
  - wake pulse when the wake word is detected
  - sustained pulse while the assistant is active
  - transcript bubble after speech is captured
  - intent, plan, and status display during processing
  - research progress display during web-search states
  - top citations from the latest result
  - recent history summaries
  - short reply bubble before collapsing back down
- HUD interaction currently includes:
  - `Yes` / `No` confirmation buttons
  - text entry for clarification or typed follow-up submission
- HUD window can be dragged and its position is saved in settings
- HUD state is driven directly from assistant and tray events rather than log polling

### Runtime State Tracking

- assistant request flow now uses explicit runtime states
- state transitions are logged to history with:
  - `state_from`
  - `state_to`
  - `correlation_id`
  - `conversation_id`
- current active states cover:
  - boot / idle
  - wake listening
  - command capture
  - transcription
  - understanding
  - planning
  - research sub-steps
  - execution
  - speaking
  - follow-up wait
  - clarification
  - awaiting confirmation
  - error
  - shutdown

### Structured History

- Request and runtime history is written to JSONL
- startup events are also written, so the history exists even before the first spoken request
- Each event stores:
  - timestamp
  - event kind
  - summary
  - pin flag
  - correlation id
  - structured payload

### Capability Registry & LLM Fallback Routing

- Centralized capabilities registry detailing all 33 intents, descriptions, required/optional slots, and query examples.
- Injects capability registry schema and examples directly into the LLM system prompt in [llm.py](file:///C:/Users/user/OneDrive/Documents/projects/Desktop%20voice%20assitant/src/desktop_voice_assistant/llm.py).
- Implements LLM-based intent routing in `OllamaAssistant` to parse user queries into structured intents and slots using the capability schema.
- Automatic routing fallback in `DesktopAssistant` when the regex-based `IntentRouter` returns `unsupported`.
- Full unit tests for the fallback mechanism in [test_assistant.py](file:///C:/Users/user/OneDrive/Documents/projects/Desktop%20voice%20assitant/tests/test_assistant.py).

### Contextual Database Retrieval & Syncing

- Integrates structured memory tables in SQLite: `tasks`, `task_embeddings`, `conversation_turns`, and `conversation_embeddings`.
- Automatically syncs all task mutations and completed conversation turns to SQLite in the background.
- Embeds tasks and conversation turns using local semantic embeddings for hybrid vector + keyword search context retrieval.
- Prefetches semantic history and task relevance scores to inject as context into LLM Q&A prompts.

### App-Specific Helpers

- **Notepad Helper**: Automatically opens or focuses Notepad, dictates content, triggers standard save dialogue shortcut (`Ctrl+S`), resolves clean Documents paths, and saves with automatic extension/dot normalization (e.g. recovering "notes txt" to "notes.txt").
- **Browser Helper**: Automatically triggers web search queries and bookmarks the resulting page using browser shortcut hotkeys (`Ctrl+D` + `Enter`).
- **VS Code Helper**: Automatically focuses or launches VS Code, and triggers the terminal pane opening shortcut (`Ctrl+``).

### UI Control Recognition & Automation

- Implements click/double-click coordinates mapping using `pyautogui` for basic button clicking.
- Implements text dictation/writing at coordinate points.
- Implements `pywinauto` child window UI control resolution based on UIA accessibility tree matching when library is present.

### Verification Baseline

- automated test suite currently passes:
  - `106/106`

## Implemented But Limited

### App Opening

- works for clean commands like `open calculator`
- now normalizes some noisy variants
- remembers successful fuzzy or recovered spoken aliases for later reuse
- can resolve many installed Windows apps outside the explicit allowlist
- still limited for more complex multi-step instructions and heavily mis-transcribed app names

### File Search

- current search roots are intentionally narrow:
  - Desktop
  - Documents
  - Downloads
  - current working directory
- best-match opening works for common cases
- multi-result disambiguation is not implemented yet

### Natural Commands

- better than initial version
- still rule-based
- can miss malformed or heavily mis-transcribed speech
- app names and app-launch phrases are improved, but multi-step spoken tasks are still out of scope
- clipboard phrasing currently covers a narrow command set
- focus phrasing currently covers direct commands such as `switch to notepad` and `switch back`
- follow-up handling is narrow and pattern-based, not general conversational reasoning yet

### HUD Limits

- the current HUD is a first-pass tkinter overlay, not a full polished desktop shell
- it does not yet show:
  - full settings controls
  - richer inline history navigation
  - richer citation interaction than title-only display

### Web Research Limits

- current search and scrape path is intentionally simple
- source ranking is heuristic, not full agentic planning yet
- semantic recall depends on the local embedding model being available and warmed
- live conflict detection is heuristic, not source-verified reasoning

### Assistant Personality

- assistant identity defaults to `Jarvis`
- response style defaults to `stark-butler`
- confirmations stay brief, formal, and slightly dry rather than casual
- generated answers are guided toward clipped status updates and restrained wit

## Not Implemented Yet

- true multi-step desktop workflows
- custom wake words
- spoken news, currency, holiday, or timezone features
