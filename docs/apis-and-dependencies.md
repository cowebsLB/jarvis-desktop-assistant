# APIs And Dependencies

## Local Runtime Dependencies

### Python

- runtime language for the whole app

### Ollama

- local model hosting for QA
- currently used model:
  - `qwen2.5-coder:1.5B`
- runtime prompt now steers answers toward a concise Stark-house butler cadence
- also used to summarize scraped web results and answer from stored archive context
- also used for local archive embeddings through:
  - `nomic-embed-text`
- embedding availability is now surfaced as runtime downgrade status rather than failing silently

### requests

- HTTP client for:
  - weather APIs
  - internal web search retrieval
  - page fetching for research

### faster-whisper

- local speech-to-text engine
- default model:
  - `base.en`
- runtime configuration:
  - device: `cpu`
  - compute type: `int8`

### pyttsx3

- offline text-to-speech on Windows
- currently used with automatic preferred-voice selection when the machine has multiple voices installed

### winsound

- Windows audible cue output for listen-start feedback

### openwakeword

- wake word detection
- configured to use ONNX inference

### onnxruntime

- inference backend for wake word detection

### pystray

- tray icon runtime

### tkinter

- built-in Windows UI toolkit used for the floating HUD overlay

### pyautogui

- text typing into active window
- click, double-click, and write operations at screen coordinate points

### pywinauto (Optional)

- automation of child window controls (e.g., buttons, inputs) using accessibility UIA tree bindings

### sqlite3

- built-in local database engine for long-lived research archive, tasks list, task embeddings, conversation turns, and conversation embeddings

## External APIs

### Open-Meteo Geocoding API

- purpose:
  - convert place name to coordinates
- used by:
  - `weather.py`
- auth:
  - no API key required
- docs:
  - https://open-meteo.com/en/docs/geocoding-api

### Open-Meteo Forecast API

- purpose:
  - current conditions and daily forecast
- used by:
  - `weather.py`
- auth:
  - no API key required
- docs:
  - https://open-meteo.com/en/docs

### DuckDuckGo HTML Search

- purpose:
  - retrieve web result pages without opening a browser
- used by:
  - `research.py`
- auth:
  - no API key required

### openWakeWord Model Assets

- downloaded model resources for ONNX wake-word operation
- source:
  - package-managed downloads from openWakeWord release assets

## Runtime Data Files

### JSONL History

- path:
  - `%USERPROFILE%\\.desktop_voice_assistant\\history.jsonl`
- purpose:
  - searchable structured request and runtime history
- format:
  - one JSON object per line
- startup writes an `app_started` event so the file is initialized immediately

### HUD Settings

- path:
  - `%USERPROFILE%\\.desktop_voice_assistant\\settings.json`
- purpose:
  - store HUD enablement and saved floating position
- current keys:
  - `hud_enabled`
  - `hud_position_x`
  - `hud_position_y`

### App Memory

- path:
  - `%USERPROFILE%\\.desktop_voice_assistant\\app_memory.json`
- purpose:
  - store learned spoken aliases for app names
- format:
  - JSON mapping of spoken alias to canonical app name with usage count

### Research Archive

- path:
  - `%USERPROFILE%\\.desktop_voice_assistant\\assistant.db`
- purpose:
  - store fetched web pages, snippets, summaries, original search queries, freshness timestamps, and semantic embeddings for later reuse
- format:
  - local SQLite database

## Discovery Sources

### public-apis

- used as a discovery index for possible future API integrations
- not used as a runtime API itself
- repo:
  - https://github.com/public-apis/public-apis
