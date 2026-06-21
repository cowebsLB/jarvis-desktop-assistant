# Jarvis Desktop Assistant

![Platform](https://img.shields.io/badge/platform-Windows%20first-0078D6)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![Voice](https://img.shields.io/badge/STT-faster--whisper-2ea44f)
![LLM](https://img.shields.io/badge/LLM-Ollama%20%2B%20Gemini-black)
![Mode](https://img.shields.io/badge/runtime-local--first%20hybrid-8A2BE2)
![Status](https://img.shields.io/badge/status-active%20development-orange)

Local-first desktop voice assistant for Windows with wake word support, offline speech-to-text, offline text-to-speech, local LLM answering, optional Gemini fallback for harder requests, internal web research, and safe desktop control.

This project is building toward a practical desktop assistant that feels conversational without depending on cloud voice APIs for the core loop.

## Highlights

- Local `faster-whisper` speech-to-text
- Offline `pyttsx3` text-to-speech with a more tailored assistant tone
- Optional always-on wake word via `openwakeword`
- Ollama-backed local question answering with optional Gemini fallback for complex prompts
- Internal web search, scraping, summarization, and local archive recall
- Safe desktop control for apps, folders, files, and dictation
- Floating HUD orb with live wake/listen/process/reply feedback
- HUD overlay toggle and settings panel from the tray
- Runtime state machine, structured JSONL history, and short follow-up memory
- Productivity layer for timers, reminders, alarms, tasks, and quick notes
- Windows system tray runtime with manual controls

## Current Capabilities

- Wake on `hey jarvis`
- Type into the focused window
- Copy, paste, read, and save clipboard contents
- Focus an existing app window or cycle to the next or previous window
- Open installed apps, allowlisted sites, common folders, and matched local files
- Handle broader launch phrasing such as `open`, `launch`, `start`, `go to`, and `visit`
- Answer weather questions
- Calculate expressions locally
- Research the web without forcing a browser-first flow
- Route simple QA to the local model and heavier reasoning/context-heavy QA to Gemini when enabled
- Answer more cautiously when live evidence is thin, conflicting, or archive notes are stale
- Show a draggable floating HUD with orb pulse and processing bubble
- Collapse or expand the HUD, click cited sources, and toggle the overlay from the tray
- Use HUD confirmation buttons and text input for follow-up / clarification flows
- Reuse recent context for follow-ups like `open it`, `summarize that`, and `search again`
- Ask for clarification or confirmation when the target is ambiguous
- Set timers, reminders, alarms, tasks, and quick notes
- Adjust assistant style, confirmation policy, archive behavior, and wake cue from the settings panel
- Use a scrollable settings panel with microphone auto-detect fallback to the system default input

## Example Commands

```text
Hey Jarvis, open notepad
Hey Jarvis, visit youtube
Hey Jarvis, open downloads folder
Hey Jarvis, open file budget report
Hey Jarvis, what's on my clipboard
Hey Jarvis, save clipboard to note
Hey Jarvis, switch to notepad
Hey Jarvis, switch back
Hey Jarvis, calculate two plus two
Hey Jarvis, what's the weather in Beirut
Hey Jarvis, search the web for python testing best practices
Hey Jarvis, summarize that
```

## Architecture

The runtime loop is:

1. Wake word or tray action triggers a request.
2. Audio is captured with adaptive silence detection.
3. Speech is transcribed locally.
4. A rule-based router selects an intent, with an intelligent LLM-based fallback when regex parsing fails.
5. The assistant executes a desktop action, weather lookup, local QA response, hybrid local-plus-Gemini QA response, or internal research flow.
6. The reply is spoken and the request is recorded in structured history.

Core modules:

- `src/desktop_voice_assistant/assistant.py`: request orchestration and multi-step handling
- `src/desktop_voice_assistant/speech.py`: wake word, STT, and TTS
- `src/desktop_voice_assistant/intent_router.py`: intent routing and slot extraction
- `src/desktop_voice_assistant/capabilities.py`: centralized registry of intents, slots, and descriptions used for LLM fallback routing
- `src/desktop_voice_assistant/actions.py`: desktop actions and launch logic
- `src/desktop_voice_assistant/research.py`: search, fetch, summarize, archive
- `src/desktop_voice_assistant/secret_store.py`: local non-repo storage for API secrets
- `src/desktop_voice_assistant/productivity.py`: timers, reminders, alarms, and tasks
- `src/desktop_voice_assistant/settings_ui.py`: tray-launched settings panel
- `src/desktop_voice_assistant/state_manager.py`: runtime state transitions
- `src/desktop_voice_assistant/session.py`: short follow-up memory

## Quick Start

### 1. Install dependencies

```powershell
pip install -e .[dev]
```

Optional wake word support:

```powershell
pip install -e .[wakeword]
```

If dependency installation is slow on this machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

### 2. Pull the local Ollama model

```powershell
ollama pull qwen2.5-coder:1.5B
```

### 3. Start the assistant

```powershell
dva
```

### Optional: enable Gemini fallback

Gemini is optional and only used for more complex requests when enabled.

- Store the API key locally in `%USERPROFILE%\.desktop_voice_assistant\secrets.json`
- Turn on `Enable Gemini Complexity Fallback` in the settings panel
- Choose a Gemini model such as `gemini-3.5-flash`

### 4. Warm the speech model once

Use the tray menu item `Warm speech model` after first install to prime the local `faster-whisper` cache.

## Requirements

- Windows
- Python `3.11+`
- Ollama installed locally
- Audio input device configured in Windows

## Project Status

Implemented now:

- Wake word and manual listen path
- Local speech and local TTS
- Weather, QA, hybrid model routing, and internal web research
- Structured history and explicit runtime states
- Floating HUD with clickable citations, collapse control, and tray visibility toggle
- Follow-up memory for short conversational chains
- Clarification and confirmation for ambiguous actions
- First-pass desktop control for apps, folders, files, clipboard helpers, and calculations
- Productivity basics and a tray-launched settings panel

Still in progress:

- Richer multi-step desktop workflows
- Long-term conversational memory
- Custom wake words

## Safety Boundaries

This repo is intentionally conservative for voice-triggered local actions.

- No arbitrary shell execution by voice
- No destructive file operations by voice
- No free-form system mutation path
- Ambiguous launches can require confirmation before execution

## Docs

- [Documentation index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Feature map](docs/features.md)
- [Issues and fixes](docs/issues-and-fixes.md)
- [Roadmap](docs/roadmap.md)
- [Contributing guide](CONTRIBUTING.md)

## Testing

Run the test suite with:

```powershell
python -m pytest
```

Run the full repo verification pass with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

That check currently runs:

- `pytest`
- `ruff check src tests`
- `pyproject-build`

Current baseline: `121/121` passing tests.

## Local Data

The assistant stores its local state under `%USERPROFILE%\.desktop_voice_assistant\`.

Important files:

- `settings.json`: runtime settings
- `secrets.json`: local API secrets such as the optional Gemini API key
- `assistant.db`: archived research
- `clipboard-notes.md`: saved clipboard notes
- `history.jsonl`: structured request and state history
- `assistant.log`: runtime log output

## Contributing

This repo is still early-stage and Windows-first. If you contribute, keep changes:

- local-first where practical
- explicit about safety boundaries
- covered by tests when behavior changes
- reflected in the docs under [`docs/`](docs/README.md)

For the full workflow and contribution expectations, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Notes

- Wake word support uses `openwakeword` when available. If wake initialization fails, the tray app still works with manual listening.
- TTS stays local via `pyttsx3` and prefers a better installed Windows voice such as `Zira` when available.
- Web questions no longer have to open the browser first; the assistant can search, scrape, summarize, and store results locally.
