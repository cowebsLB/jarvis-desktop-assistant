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
- `calculate`
- `open_target`
- `open_folder`
- `open_file`
- `web_search`
- `recall_memory`
- `weather`
- `qa`
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
- calculate local arithmetic expressions with spoken results
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

### Direct Web Research

- web search no longer has to open the browser
- Jarvis now:
  - searches the web internally
  - fetches and scrapes source pages
  - summarizes the findings aloud
  - stores the material locally for later recall
- research answers append a brief offer to open sources if needed

### Local Research Archive

- stored in local SQLite
- keeps fetched pages, snippets, summaries, original queries, and timestamps
- can answer later follow-up questions from stored notes
- supports recall prompts like `summarize python testing`
- stores local embeddings for semantic recall when the embedding model is available

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

### Verification Baseline

- automated test suite currently passes:
  - `52/52`

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
- follow-up handling is narrow and pattern-based, not general conversational reasoning yet

### Web Research Limits

- current search and scrape path is intentionally simple
- source ranking is heuristic, not full agentic planning yet
- semantic recall depends on the local embedding model being available and warmed

### Assistant Personality

- assistant identity defaults to `Jarvis`
- response style defaults to `stark-butler`
- confirmations stay brief, formal, and slightly dry rather than casual
- generated answers are guided toward clipped status updates and restrained wit

## Not Implemented Yet

- true multi-step desktop workflows
- custom wake words
- conversational memory
- spoken news, currency, holiday, or timezone features
