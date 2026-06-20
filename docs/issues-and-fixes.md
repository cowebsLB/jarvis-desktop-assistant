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
