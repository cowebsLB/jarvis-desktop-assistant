# TODO

## Now

### Implementation Sequence

#### 3. Clarification And Confirmation Flow

- Goal:
  - stop executing unclear or risky actions blindly
- Expected modules:
  - `src/desktop_voice_assistant/intent_router.py`
  - `src/desktop_voice_assistant/assistant.py`
  - `src/desktop_voice_assistant/response_style.py`
  - `src/desktop_voice_assistant/actions.py`
- Deliverables:
  - transcript-confidence thresholds
  - yes / no / cancel confirmation handling across more than fuzzy app opens
  - risky-action classification
  - richer history markers for confirmation and clarification prompts
- Test checkpoint:
  - add tests for:
    - destructive request requires confirmation

#### 4. Desktop Control Foundation

- Goal:
  - expand useful local actions before deeper automation
- Expected modules:
  - `src/desktop_voice_assistant/intent_router.py`
  - `src/desktop_voice_assistant/actions.py`
  - add `src/desktop_voice_assistant/filesystem_actions.py` if needed
- Deliverables:
  - clipboard helpers
  - focus-switching and app-window targeting hooks
- Test checkpoint:
  - add tests for:
    - clipboard action dispatch
    - focus-switching helper dispatch

#### 5. Research Reliability Pass

- Goal:
  - make research answers more trustworthy and stable
- Expected modules:
  - `src/desktop_voice_assistant/research.py`
  - `src/desktop_voice_assistant/archive.py`
  - `src/desktop_voice_assistant/embeddings.py`
  - `src/desktop_voice_assistant/assistant.py`
- Deliverables:
  - improved source ranking
  - stale/freshness metadata in archive
  - better extraction cleanup
  - evidence-required answer path for live factual queries
  - explicit embedding warmup and downgrade status
- Test checkpoint:
  - add tests for:
    - stale source marking
    - conflicting sources produce cautious answer
    - missing embedding model falls back to keyword search
    - research answer includes sources when available

#### 6. End-To-End “Now” Stabilization

- Goal:
  - close the slice cleanly before moving to HUD and broader memory work
- Expected modules:
  - whole repo touch-up
  - docs under `docs/`
  - `README.md`
  - `TODO.md`
- Deliverables:
  - docs updated for shipped behavior
  - tray runtime restarted on new build
  - settings migrations for any new config fields
  - regression suite expanded
- Test checkpoint:
  - full `python -m pytest`
  - manual smoke tests:
    - wake word -> weather
    - web research -> follow-up summary
    - risky action -> confirmation
    - calculator
    - clipboard helper
    - local file open

### Assistant Flow And State

- Add a session manager for:
  - pending confirmation
  - active multi-step task
- Add a planner layer that decides:
  - single-step action
  - multi-step action
  - clarification needed
  - confirmation needed
  - local recall vs fresh research

### Clarification And Follow-Up

- Add better handling of transcription uncertainty.
- Add confidence-aware clarification when STT is doubtful.
- Add alternate-interpretation prompts when the transcript is ambiguous.
- Add short multi-turn follow-up handling for:
  - `the second one`
- Add confirmation flow for risky actions:
  - delete
  - overwrite
  - send email
  - power actions
  - ambiguous targets

### Desktop Control Foundation

- Add richer browser and site-opening phrases.
- Add clipboard helpers:
  - copy selection
  - paste clipboard
  - save clipboard to note
  - read clipboard back
- Add file and folder helpers:
  - broader folder coverage beyond the current common aliases
  - file-result disambiguation when several local matches are close
- Add focus-switching and app-window targeting.

### Research Reliability

- Improve source ranking beyond the current heuristic approach.
- Add freshness tracking and stale-source handling.
- Add better page parsing and extraction quality.
- Add result verification so live factual answers require evidence before confident output.
- Add explicit embedding warmup and status handling.
- Add graceful downgrade when the embedding model is missing.

### Testing For The Current Next Slice

- Add tests for follow-up conversation handling.
- Add tests for stale-source and source-conflict handling.

## Next

### UI And Settings

- Add a compact desktop HUD.
- Surface current state in both the tray title and the HUD.
- HUD should show:
  - current state
  - live transcript
  - parsed intent
  - planned steps
  - research progress
  - citations
  - confirmations
  - recent history
- Add a proper settings UI instead of JSON-only editing.
- Add settings for:
  - voice style
  - TTS engine
  - follow-up timeout
  - push-to-talk
  - confirmation policy
  - web fetch limits
  - archive behavior
  - embedding model
  - proactive features

### Conversation, Memory, And Autonomy

- Add conversational memory and broader context across turns.
- Add long-term preference memory:
  - preferred apps
  - preferred locations
  - favorite sites
  - repeated aliases
- Add memory summarization so prompts stay compact.
- Keep broad autonomy for safe actions without re-asking.
- Add a capability registry so tools and actions are discoverable in one place.
- Add retrieval over:
  - archived web research
  - future conversation summaries
  - future reminders and tasks
  - learned preferences

### Better Desktop Automation

- Add app-specific helpers for common apps instead of generic launching only.
- Add browser automation beyond simple search:
  - open result pages
  - summarize current page
  - click basic controls
  - fill simple forms
- Add Windows UI automation for desktop apps beyond raw typing.
- Add calculator workflow support inside opened apps when needed.
- Add tests for browser automation helpers.
- Add tests for Windows UI automation wrappers where possible.

### Productivity Basics

- Add reminders.
- Add timers.
- Add alarms.
- Add quick notes.
- Add local task list management.
- Add queued spoken notifications for reminders and timers.
- Add tests for proactive reminders and timers.

## Later

### Advanced Desktop And Agent Behavior

- Add true multi-step desktop workflows.
- Add multi-step research planning.
- Add semantic chunking instead of storing only coarse page text.
- Add richer archive queries:
  - compare past research runs
  - summarize stored notes on a topic
  - refresh old research
- Add archive pruning and retention controls.
- Add research-topic pinning for later revisits.
- Add scheduled refresh for subscribed topics.
- Add typed tool results so the model reasons over structured outputs instead of loose text.

### Voice And Presence

- Add optional push-to-talk fallback.
- Add configurable assistant voice profiles in settings.
- Replace `pyttsx3` later with a stronger local TTS engine such as Piper.
- Add response variation so confirmations do not sound repetitive over time.
- Add barge-in handling so speech can interrupt Jarvis.
- Add custom wake word support.

### Proactive Assistant Features

- Add ambient proactive behavior that is user-configured, not surveillance-driven.
- Add daily summary generation.
- Add morning and evening briefings.
- Add `proactive_pending` and `suspended` runtime states once proactive jobs exist.

### Integrations And APIs

- Add more live public API integrations discovered via the `public-apis` index.
- Evaluate a news feature with a no-key or low-friction provider.
- Add currency and exchange-rate queries.
- Add a geocoding fallback provider.
- Add public holiday queries.
- Add timezone and world-clock queries.
- Add dictionary and definitions support.
- Add personal productivity integrations:
  - Google Calendar
  - Gmail
- Keep send/edit actions behind confirmation.
- Add integration tests for future Gmail and Calendar adapters.

### Model And Retrieval Expansion

- Add richer local reasoning model options.
- Add model routing later if the small local model is not enough for certain tasks.

## Blocked / Depends On

- Full HUD work depends on the state machine and session manager landing first.
- Reliable multi-step workflows depend on:
  - planner layer
  - confirmation flow
  - better window targeting
- Gmail and Calendar integrations depend on:
  - settings UI or a safe auth/config flow
  - confirmation system
  - structured task/reminder storage
- Proactive summaries depend on:
  - reminders / tasks
  - conversation memory
  - archive freshness tracking
- Stronger TTS replacement depends on deciding:
  - offline engine choice
  - voice packaging and install flow

## Recently Completed

- Runtime state machine with explicit state transitions.
- Tray title bound to runtime state.
- State transition logging into structured history.
- Short-lived session manager with:
  - conversation id reuse
  - follow-up timeout handling
  - last query tracking
  - last opened target tracking
  - last source tracking
- Narrow follow-up commands:
  - `open it`
  - `summarize that`
  - `search again`
  - `search again but for today`
- Initial clarification and confirmation flow for:
  - missing follow-up context
  - fuzzy app matches
- Confirmation turn execution:
  - `yes` now executes the approved action instead of re-asking
  - `no` now clears the pending action cleanly
- Clarification turn handling:
  - contextless `open it` now asks what to open instead of guessing
- State-machine follow-up fixes:
  - `awaiting_confirmation -> transcribing`
  - `clarifying -> transcribing`
  - `speaking -> awaiting_confirmation`
  - `speaking -> clarifying`
- Regression coverage added for:
  - contextless `open it`
  - fuzzy app confirmation
  - confirmation accept / cancel paths
- Desktop control foundation, first pass:
  - direct `calculate` intent with safe local evaluation
  - natural calculator phrasing like `calculate two plus two on the calculator app`
  - common folder opening:
    - Desktop
    - Documents
    - Downloads
    - Music
    - Pictures
    - Videos
    - Home
  - local file search by name with best-match opening
  - broader site/app opening phrases:
    - `launch`
    - `start`
    - `go to`
    - `visit`
- Regression coverage added for:
  - calculator routing and execution
  - folder opening resolution
  - file search best-match opening
  - broader open-target phrasing
