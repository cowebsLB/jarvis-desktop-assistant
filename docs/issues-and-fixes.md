# Issues And Fixes

This file tracks bugs, investigation outcomes, and whether each fix is quick, partial, or intended to be permanent.

## Legend

- `Quick fix`: tactical patch, acceptable for now, may need redesign later
- `Permanent`: intended long-term behavior for the current architecture
- `Partial`: improved behavior, but follow-up work is still expected

## Issue Log

### 1. Empty workspace / no project scaffold

- Symptom:
  - no codebase existed in the workspace
- Root cause:
  - greenfield project
- Resolution:
  - created full Python package, tray runtime, tests, settings, and docs structure
- Fix type:
  - `Permanent`

### 2. Runtime dependencies too heavy for one-shot install

- Symptom:
  - `pip install -e .[dev]` timed out repeatedly
- Root cause:
  - large dependency stack and unstable network / slow download path
- Resolution:
  - made wake word optional
  - added staged bootstrap flow
  - installed dependencies in smaller groups
- Fix type:
  - `Partial`

### 3. App startup failed when the Vosk model was missing

- Symptom:
  - startup would fail before tray use
- Root cause:
  - STT required the model at construction time with no fallback
- Resolution:
  - added degraded `MissingSpeechToText`
  - tray can start before model install
- Fix type:
  - `Permanent`

### 4. Vosk model download was brittle

- Symptom:
  - partial downloads and timeout failures
- Root cause:
  - one-shot Python download path was unreliable on this connection
- Resolution:
  - added streamed retry logic in code
  - used BITS successfully during setup
- Fix type:
  - `Partial`

### 5. Wake word failed after `openwakeword` install

- Symptom:
  - listener still failed even though package was installed
- Root cause:
  - default `tflite` path required `tflite-runtime`
- Resolution:
  - forced ONNX inference path
- Fix type:
  - `Permanent`

### 6. Wake word phrase mismatch in saved settings

- Symptom:
  - saved phrase `hey desktop` caused wake listener failures
- Root cause:
  - custom phrase was not compatible with pretrained wake word models
- Resolution:
  - migrated unsupported values to `hey jarvis`
- Fix type:
  - `Permanent`

### 7. Missing `Path` import caused startup crash

- Symptom:
  - app crashed during STT initialization
- Root cause:
  - `Path` import was accidentally removed from `speech.py`
- Resolution:
  - restored the import
- Fix type:
  - `Quick fix`

### 8. Wake word triggered many overlapping recordings

- Symptom:
  - one wake utterance created many simultaneous request threads
  - assistant appeared to close instantly or misbehave
- Root cause:
  - no single-flight request guard
  - wake listener stayed active during request recording
- Resolution:
  - added request lock
  - ignored triggers while a request is active
  - paused wake listener during request handling
- Fix type:
  - `Permanent`

### 9. Weather requests were treated as unsupported

- Symptom:
  - `check today's weather in Lebanon` was rejected
- Root cause:
  - router only recognized a narrow set of command shapes
- Resolution:
  - added weather intent and live weather service
- Fix type:
  - `Permanent`

### 10. Spoken phrasing was too rigid

- Symptom:
  - extra words made valid commands miss intent detection
- Root cause:
  - strict prefix matching and weak normalization
- Resolution:
  - added spoken command normalization
  - removed wake-word leftovers and polite fillers
- Fix type:
  - `Partial`

### 11. `open chrome` crashed when configured path was missing

- Symptom:
  - `FileNotFoundError` during app launch
- Root cause:
  - hardcoded Chrome path did not exist on this machine
- Resolution:
  - added absolute-path validation
  - added executable lookup fallback
  - added browser fallback for Chrome
- Fix type:
  - `Partial`

### 12. `open the calculator up` failed allowlist matching

- Symptom:
  - target extracted as `the calculator up`
- Root cause:
  - spoken app names were not normalized before allowlist lookup
- Resolution:
  - added target normalization and alias mapping
- Fix type:
  - `Partial`

### 13. No clear cue for when command capture started

- Symptom:
  - user could not tell exactly when Jarvis was listening after the wake word
- Root cause:
  - no listen-start audio feedback
- Resolution:
  - added a short audible wake/listen cue
- Fix type:
  - `Permanent`

### 14. Fixed recording window was awkward for real speech

- Symptom:
  - rigid capture windows made the interaction feel brittle
- Root cause:
  - STT used a constant recording duration
- Resolution:
  - added adaptive end-of-speech detection based on silence
- Fix type:
  - `Partial`

### 15. Plain text logs were not enough for searchable progress history

- Symptom:
  - runtime logs existed, but they were not structured for filtering, pinning, or event correlation
- Root cause:
  - only line-based text logs were being written
- Resolution:
  - added structured JSONL history with summaries, pins, and correlation ids
- Fix type:
  - `Permanent`

### 16. Failure responses were too generic to be useful

- Symptom:
  - Jarvis would say a request was unsupported without explaining what it heard or what to try instead
- Root cause:
  - fallback responses were generic and action-layer only
- Resolution:
  - moved unsupported feedback into assistant-level transcript-aware handling
  - added targeted suggestions for silence, app-launch phrasing, search phrasing, and calculator workflow requests
- Fix type:
  - `Partial`

### 17. App launch capability was too limited by the allowlist

- Symptom:
  - Jarvis could not open many installed apps unless they were manually listed in settings
- Root cause:
  - app resolution stopped at the explicit allowlist
- Resolution:
  - added installed-app discovery through PATH, Windows App Paths registry entries, and Start Menu shortcut matching
- Fix type:
  - `Partial`

### 18. App names still failed when STT mangled them badly

- Symptom:
  - app requests like `VS Code` were transcribed as variants such as `vs good` or `of us could`
- Root cause:
  - installed-app discovery can only work after the spoken target is normalized close enough to a real app name
- Resolution:
  - added known mis-hearing normalization for observed variants
  - added persistent app-memory alias storage for future recovered names
- Fix type:
  - `Partial`

### 19. Vosk was too brittle for real desktop speech

- Symptom:
  - transcription quality and setup flow were not good enough for casual desktop use
- Root cause:
  - the active STT path depended on a separate Vosk model asset and had weaker recognition quality for noisy, natural requests
- Resolution:
  - switched the active STT backend to `faster-whisper`
  - replaced model download flow with local model warmup
- Fix type:
  - `Permanent`

### 20. TTS personality sounded too flat

- Symptom:
  - spoken responses felt plain and generic
- Root cause:
  - stock confirmation strings and default voice selection were too neutral
- Resolution:
  - added personalized response phrasing
  - updated the QA system prompt to a concise Jarvis-like voice
  - auto-select a better installed Windows voice when available
- Fix type:
  - `Partial`

### 21. Older settings files crashed after the STT migration

- Symptom:
  - startup or model warmup failed with an unexpected `stt_model_path` argument error
- Root cause:
  - the saved settings file still contained legacy Vosk fields after the config schema changed
- Resolution:
  - filtered unknown keys during settings load
  - preserved a simple migration path from old settings into the new `faster-whisper` config
- Fix type:
  - `Permanent`

### 22. Assistant personality needed a stronger premium voice

- Symptom:
  - even after the TTS cleanup, the assistant still sounded too generic and casual
- Root cause:
  - response phrasing and QA prompt tone were not distinctive enough
- Resolution:
  - shifted the default style to a Stark-house butler voice
  - tightened confirmations and fallback responses to sound more formal and composed
  - aligned generated answers and weather summaries to the same cadence
  - explicitly avoided direct imitation of a copyrighted character while keeping a similar feel
- Fix type:
  - `Partial`

### 23. Web search still depended on opening the browser

- Symptom:
  - Jarvis could search only by launching the browser, which broke the assistant flow and gave it no reusable knowledge
- Root cause:
  - `web_search` was just a browser action with no retrieval or storage layer
- Resolution:
  - added internal search, page fetching, scraping, summarization, and local archival
  - wired QA to reuse stored research when relevant
- Fix type:
  - `Partial`

### 24. Archive recall was too dependent on exact keywords

- Symptom:
  - follow-up questions with different wording could miss useful stored research
- Root cause:
  - archive retrieval only used simple keyword matching
- Resolution:
  - added local embedding generation through Ollama
  - added semantic ranking over stored research with keyword fallback when embeddings are unavailable
- Fix type:
  - `Partial`

### 25. Request lifecycle state was implicit and hard to build on

- Symptom:
  - tray labels, logs, and future UI work had no single source of truth for what the assistant was currently doing
- Root cause:
  - runtime progress was inferred from scattered strings and control flow instead of an explicit state model
- Resolution:
  - added a dedicated runtime state manager
  - logged state transitions into structured history
  - bound tray title updates to the runtime state
- Fix type:
  - `Permanent`

### 26. Follow-up commands had no context to attach to

- Symptom:
  - requests like `open it` or `summarize that` had no shared session context, so they could not refer to the previous result
- Root cause:
  - every request was handled as a fully isolated turn with no short-lived conversation snapshot
- Resolution:
  - added a session manager with a follow-up timeout
  - stored the last research query, last opened target, and last research sources
  - reused that context for narrow follow-up commands
- Fix type:
  - `Partial`

### 27. Contextless follow-up phrasing could trigger the wrong app

- Symptom:
  - `open it` without prior context could fall through to fuzzy app matching and attempt an unrelated launch
- Root cause:
  - follow-up pronouns were being treated as literal app targets when no reusable session context existed
- Resolution:
  - added assistant-level clarification for contextless `open it` style requests
  - pending clarification is now stored and resumed on the next turn
- Fix type:
  - `Permanent`

### 28. Fuzzy app confirmation could loop forever

- Symptom:
  - saying `yes` after `open spotfy` could ask the same confirmation again instead of launching Spotify
- Root cause:
  - the confirmed intent re-entered fuzzy preview with no marker that the user had already approved the recovered target
- Resolution:
  - tagged confirmed intents in session handoff
  - bypassed fuzzy preview when the action was already confirmed
- Fix type:
  - `Permanent`

### 29. Confirmation and clarification follow-up turns broke state transitions

- Symptom:
  - the next spoken turn after a prompt could fail with invalid transitions such as `awaiting_confirmation -> transcribing`
- Root cause:
  - the runtime state machine did not allow direct transcription from pending prompt states
  - reply speaking always fell through to generic follow-up state handling
- Resolution:
  - allowed direct `transcribing` transitions from `awaiting_confirmation` and `clarifying`
  - returned to `awaiting_confirmation` or `clarifying` after spoken prompts when pending state still existed
- Fix type:
  - `Permanent`

### 30. Natural calculator requests still failed even after adding math support

- Symptom:
  - phrases like `calculate two plus two on the calculator app` still failed instead of producing a result
- Root cause:
  - the first calculator parser only handled symbol-heavy expressions and kept irrelevant trailing app words
- Resolution:
  - stripped calculator-app filler phrases from math expressions
  - added simple number-word normalization before safe evaluation
- Fix type:
  - `Partial`

### 31. Desktop control was still too narrow for basic local navigation

- Symptom:
  - Jarvis could launch apps, but could not open common folders or locate local files by name
- Root cause:
  - the action layer had no filesystem helper path beyond app and site launching
- Resolution:
  - added common-folder aliases
  - added local file search across common user roots
  - added best-match file opening for direct requests
- Fix type:
  - `Partial`

### 32. Site-opening language was too strict

- Symptom:
  - natural phrases such as `visit youtube` or `go to gmail` were not routed as open requests
- Root cause:
  - open-target routing only recognized `open ...`
- Resolution:
  - expanded routing to accept `launch`, `start`, `go to`, and `visit`
- Fix type:
  - `Permanent`

### 33. Desktop control still lacked basic clipboard commands

- Symptom:
  - Jarvis could open apps and files, but could not copy, paste, read the clipboard, or store clipboard text for later
- Root cause:
  - the desktop action layer had no clipboard command path or local note sink
- Resolution:
  - added clipboard intents for copy, paste, read, and save-to-note
  - wired copy and paste through safe keyboard shortcuts
  - added clipboard text retrieval and local note storage under the assistant data directory
- Fix type:
  - `Partial`

### 34. Desktop control still could not target the currently open window stack

- Symptom:
  - Jarvis could open apps, but it could not focus an already open app window or switch between current windows
- Root cause:
  - the desktop action layer had no focus-target or window-cycling path
- Resolution:
  - added focus-by-title or process-name matching for visible windows
  - added next-window and previous-window switching hooks
  - covered the routing and dispatch behavior with tests
- Fix type:
  - `Partial`

### 35. Research answers were too confident when evidence was weak

- Symptom:
  - live web answers could sound definitive even when only one usable page was fetched or when source details disagreed
- Root cause:
  - the research summarization path did not add any explicit evidence-quality note before speaking the answer
- Resolution:
  - added limited-evidence and conflict-caution notes for live research answers
  - kept source lists attached so the assistant can still open or cite what it used
- Fix type:
  - `Partial`

### 36. Archive recall hid how old stored notes were

- Symptom:
  - recalled answers from old research looked the same as fresh notes, even when the stored fetch was stale
- Root cause:
  - the archive stored timestamps, but recall did not surface freshness metadata
- Resolution:
  - added stale and age-day metadata on archive hits
  - added stale-note warnings in recall responses when stored material is old
- Fix type:
  - `Partial`

### 37. Embedding failure degraded retrieval silently

- Symptom:
  - semantic recall could stop working when the local embedding model failed, with no explicit signal that the system had fallen back
- Root cause:
  - embedding calls returned `None`, but the research flow did not surface the downgrade
- Resolution:
  - tracked embedding warm and error status
  - surfaced keyword-only fallback messaging when embeddings are unavailable
- Fix type:
  - `Permanent`

### 38. The assistant had no live visual feedback layer

- Symptom:
  - users had to infer whether Jarvis was idle, listening, processing, or replying from audio cues and tray state alone
- Root cause:
  - there was no floating visual surface connected directly to the request lifecycle
- Resolution:
  - added a draggable always-on-top HUD orb
  - wired wake, transcript, intent, reply, and runtime state events directly into the HUD
  - saved HUD position in settings
- Fix type:
  - `Partial`

### 39. The first HUD pass still lacked real interaction and deeper request context

- Symptom:
  - the initial HUD could pulse and show transcript and reply, but it could not show plan details, research progress, recent history, or let the user answer confirmations directly
- Root cause:
  - the first implementation only consumed a narrow event surface and had no path to submit typed follow-up input back into the assistant
- Resolution:
  - added HUD plan, research-progress, citation, and recent-history views
  - added inline `Yes` / `No` confirmation buttons
  - added text input for clarification and typed follow-up submission
  - added direct HUD-originated text request handling in the assistant/tray flow
- Fix type:
  - `Partial`

### 40. Launching multiple concurrent app instances causes microphone conflicts and redundant behavior

- Symptom:
  - Starting the app multiple times (either manually or via an autoupdate flow) spawns multiple concurrent taskbar/tray icons and speech recording loops, causing overlapping microphone access errors and chaotic redundant transcripts.
- Root cause:
  - There was no check at the main entry point to verify if another instance of the application was already running.
- Resolution:
  - Implemented a localhost TCP socket lock on port `47711` at the app boot phase (`app.py`). Any subsequent instances failing to bind to this port log a warning and exit cleanly instead of starting another system tray or speech loop.
- Fix type:
  - `Complete`

## Current Open Issues

### Speech mis-transcription remains a source of failure

- Example:
  - `Lebanon` heard as `eleven on`
- Status:
  - open
- Notes:
  - normalization helps only after transcription succeeds well enough

### Multi-step spoken app tasks are still unsupported

- Example:
  - `calculate two plus two on the calculator app`
- Status:
  - open
- Notes:
  - opening apps is supported
  - chained in-app actions are not yet implemented

### Clipboard phrasing is still narrow

- Example:
  - unusual variants like `stash this in my notes` may not route to clipboard note saving
- Status:
  - open
- Notes:
  - the current router covers direct clipboard phrases only

### Window targeting is still heuristic

- Example:
  - several windows from the same app may produce the wrong focus choice
- Status:
  - open
- Notes:
  - current focusing prefers visible title/process matches only
  - richer window disambiguation is still future work

### Live source ranking is still heuristic

- Example:
  - two mediocre pages may outrank a more authoritative page because the current ranking path is fetch-order plus simple conflict cues
- Status:
  - open
- Notes:
  - evidence handling is safer now
  - authority-aware ranking is still future work

### HUD is still a first-pass overlay

- Example:
  - the overlay now shows plan and confirmation context, but it is still not a polished custom desktop shell
- Status:
  - open
- Notes:
  - current implementation prioritizes low-friction live feedback first
  - richer UI polish is still future work
