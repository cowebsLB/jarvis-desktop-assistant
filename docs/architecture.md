# Architecture

## Overview

The assistant is a local Windows desktop app that runs as a system tray process. It listens for a wake word, records a short voice command, transcribes it locally, routes the transcript to an intent, executes the intent, and optionally speaks the result.

The runtime now has an explicit state manager so request progress is not inferred from tray strings alone.
It also now has a short-lived session manager for follow-up context reuse across nearby turns.

## Main Runtime Flow

1. Tray app starts.
2. Wake word listener runs in the background.
3. Wake word triggers a single active request.
4. Wake listener pauses while the request is handled.
5. Audio is recorded with adaptive silence-based endpoint detection.
6. Local STT converts speech to text.
7. Intent router classifies the text.
8. Assistant either:
  - answers through the local LLM
  - answers from stored research when relevant
  - performs direct internal web research
  - fetches live weather
  - performs a safe desktop action
9. TTS speaks the response.
10. Wake listener resumes.

## Module Map

- `app.py`
  - process entrypoint
  - loads settings
  - wires assistant dependencies
  - launches tray runtime

- `tray.py`
  - tray icon and menu
  - request lifecycle
  - wake word control
  - speech model warmup action
  - single-flight request protection

- `assistant.py`
  - request orchestration
  - STT -> intent -> action/QA/research/weather -> TTS flow
  - owns runtime state transitions for the main request flow
  - applies short-lived follow-up context before normal routing

- `speech.py`
  - local TTS adapter
  - local STT adapter using `faster-whisper`
  - wake word listener using `openwakeword`
  - preferred Windows voice selection
  - degraded fallback behavior if STT/TTS cannot initialize

- `intent_router.py`
  - spoken command normalization
  - intent classification
  - slot extraction

- `actions.py`
  - desktop typing
  - app opening
  - site opening
  - explicit browser opening path
  - app target normalization and launch fallback logic

- `research.py`
  - internal web search
  - page fetching and scraping
  - research summarization
  - archive recall
  - emits research sub-state transitions

- `archive.py`
  - SQLite storage for fetched research material
  - later recall of stored notes

- `embeddings.py`
  - local Ollama embedding calls
  - semantic archive retrieval support

- `state_manager.py`
  - legal runtime state transitions
  - transition callbacks for history and UI state

- `session.py`
  - short-lived conversation context
  - follow-up timeout handling
  - recall of last query / last opened target / last source

- `weather.py`
  - place geocoding
  - forecast retrieval
  - spoken weather summary formatting

- `llm.py`
  - Ollama client wrapper
  - concise Jarvis-style assistant system prompt

- `model_manager.py`
  - `faster-whisper` warmup helper

- `config.py`
  - settings schema
  - defaults
  - settings migration for older values

## Data and State

- User settings:
  - `%USERPROFILE%\\.desktop_voice_assistant\\settings.json`

- Research archive:
  - `%USERPROFILE%\\.desktop_voice_assistant\\assistant.db`

- Runtime log:
  - `%USERPROFILE%\\.desktop_voice_assistant\\assistant.log`

- Runtime state history:
  - written into `%USERPROFILE%\\.desktop_voice_assistant\\history.jsonl` as `state_transition` events

## Safety Boundaries

- No arbitrary shell execution by voice
- No delete/move/write file actions by voice
- App and site launches restricted to allowlists
- Browser search used as a fallback only for explicit search-like requests

## Known Architectural Tradeoffs

- Intent routing is rule-based, not model-based
  - faster and safer for core actions
  - less flexible for unusual phrasing

- Wake word uses a fixed pretrained phrase
  - practical now
  - custom wake word is not yet supported

- Intent routing is still rule-based even though STT is stronger now
  - fast and predictable
  - still limited for multi-step natural speech

- Internal research currently uses keyword recall over stored pages
  - falls back safely when embeddings are unavailable
  - now prefers embedding-backed semantic retrieval when the local embedding model is available

- Multi-turn session state still does not exist yet
  - runtime state is explicit now
  - short-lived follow-up memory exists now
  - long-term conversational/session memory is still the next layer to build
