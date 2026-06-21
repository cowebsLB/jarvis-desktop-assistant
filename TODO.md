# TODO

### Now

### Implementation Sequence

All tasks in the "Now" cycle have been completed successfully:
- **Clarification And Confirmation Flow**: Handled low-confidence transcript triggers and confirmation intercepts for risky actions (`delete_file`, `power_action`, `send_email`).
- **Desktop Control Foundation**: Expanded folder aliases and file matches.
- **Research Reliability Pass**: Implemented cosine similarity based page source ranking with TF-IDF fallback, plus semantic HTML tag prioritizing parser.
- **End-To-End Stabilization**: Expanded regression tests and fixed routing conflicts. All 130 tests passing.

### Assistant Flow And State

- [x] Add a session manager for:
  - pending confirmation
  - active multi-step task
- [x] Add a planner layer that decides:
  - single-step action
  - multi-step action
  - clarification needed
  - confirmation needed
  - local recall vs fresh research

### Clarification And Follow-Up

- [x] Add better handling of transcription uncertainty.
- [x] Add confidence-aware clarification when STT is doubtful.
- [x] Add alternate-interpretation prompts when the transcript is ambiguous.
- [x] Add confirmation flow for risky actions:
  - delete
  - overwrite
  - send email
  - power actions
  - ambiguous targets

### Desktop Control Foundation

- [x] Add richer browser and site-opening phrases.
- [x] Add file and folder helpers:
  - broader folder coverage beyond the current common aliases
  - file-result disambiguation when several local matches are close

### Research Reliability

- [x] Improve source ranking beyond the current heuristic approach.
- [x] Add better page parsing and extraction quality.
- [x] Add graceful downgrade when the embedding model is missing.

### Testing For The Current Next Slice

- [x] Add tests for follow-up conversation handling.ing.

## Next

### UI And Settings

- [x] Add settings for:
  - [x] TTS engine
  - [x] push-to-talk
  - [x] proactive features


### Conversation, Memory, And Autonomy

- [x] Keep broad autonomy for safe actions without re-asking.
- [x] Add retrieval over:
  - [x] archived web research
  - [x] future conversation summaries
  - [x] future reminders and tasks
  - [x] learned preferences

### Better Desktop Automation

- [x] Add app-specific helpers for common apps instead of generic launching only.
  - [x] Spotify: play/pause, next/previous track, volume up/down.
  - [x] Discord: mute/unmute, deafen, quick-nav to channel.
  - [x] Slack: mute/unmute, quick-nav to channel.
- [x] Add browser automation beyond simple search:
  - [x] click basic controls (browser_click_control via pywinauto or Ctrl+F fallback)
  - [x] fill simple forms (browser_fill_form via JSON or label:value pairs)
- Add Windows UI automation for desktop apps beyond raw typing.
- Add calculator workflow support inside opened apps when needed.
- Add tests for Windows UI automation wrappers where possible.

### Productivity Basics


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
- Refine model-routing heuristics and provider-specific prompts for hybrid local/Gemini QA.

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
- Ordinal follow-up commands:
  - `open the second one`
  - `summarize the second one`
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
- Desktop control foundation, clipboard pass:
  - copy selection
  - paste clipboard
  - read clipboard back
  - save clipboard to `%USERPROFILE%\.desktop_voice_assistant\clipboard-notes.md`
- Regression coverage added for:
  - clipboard routing
  - clipboard action dispatch
  - clipboard note persistence
- Desktop control foundation, focus pass:
  - focus existing app windows by visible title or process name
  - switch to next window
  - switch to previous window
- Regression coverage added for:
  - focus routing
  - focus action dispatch
  - next/previous window switching
- Research reliability pass, safety pass:
  - stale archive notes are marked and surfaced cautiously
  - live answers now warn on limited or conflicting evidence
  - embedding fallback is surfaced as keyword-only downgrade status
  - extraction cleanup removes more page noise before summarization
- Regression coverage added for:
  - stale archive hits
  - conflicting live sources
  - embedding downgrade fallback
  - research results retaining sources
- Floating HUD, first pass:
  - always-on-top draggable orb
  - wake pulse
  - active-state pulsing while listening / processing / speaking
  - transcript / intent / reply bubble
  - saved HUD position in settings
- Regression coverage added for:
  - assistant HUD event emission
- Floating HUD, completion pass:
  - planned steps display
  - research progress display
  - citations display
  - confirmations display
  - recent history display
  - inline `Yes` / `No` actions
  - typed clarification / follow-up entry
- Regression coverage added for:
  - HUD text-input request path
- Floating HUD, visual polish pass:
  - Concentric breathing/pulsing canvas orb with state colors.
  - Clickable citation links opening in default browser.
  - Compact chevron collapse/expand affordance.
  - Tray menu item to toggle HUD on/off.
- Floating HUD, runtime lifecycle pass:
  - HUD instance now stays wired through app lifetime.
  - Tray/settings HUD toggle now hides or restores the overlay instead of tearing down the event stream.
  - Startup with HUD disabled now preserves later enablement cleanly.
- Regression coverage added for:
  - Real FloatingHud class event queueing and thread-safe behavior.
  - HUD enabled/disabled state updates.
- Settings Panel GUI:
  - Styled dark settings window matching HUD styling.
  - Form fields and sliders for Assistant Name, assistant style, default location, wake word toggle, wake cue toggle, wake phrase dropdown, speech rate slider, semantic retrieval toggle, archive toggles, LLM/embedding models, fetch limits, archive recall limit, confirmation policy, HUD toggle, and follow-up timeout.
  - Dynamically saves to settings.json and synchronizes runtime values (TTS speech rate, HUD state, wake word listener) instantly on save.
- Regression coverage added for:
  - SettingsPanel class initialization and default binding.
 - Settings runtime sync pass:
  - assistant style now updates the live LLM prompt tone
  - confirmation policy now supports `smart` and `always`
  - web research archive enablement now affects persistence behavior
  - optional top-source auto-open after web answers is now wired
  - follow-up timeout, fetch limit, archive mode, and model/style changes now resync into the running assistant
 - Regression coverage added for:
  - confirmation-policy forced open-target approval
  - archive-disabled research behavior
- Productivity Basics:
  - Reminders, timers, alarms background thread scheduler and filesystem JSON database store in [productivity.py](file:///C:/Users/user/OneDrive/Documents/projects/Desktop%20voice%20assitant/src/desktop_voice_assistant/productivity.py).
  - Queued thread-safe spoken voice alarms and reminders.
  - General quick note-taking output directly appended to markdown log file.
  - CRUD action and task list management APIs.
  - Regressions test suite coverage.
- Conversational & Preference Memory:
  - Multi-turn turn accumulation and LLM context prompt construction.
  - Automated history summarization via LLM upon reaching five conversational turns threshold to maintain compact prompts.
  - Long-term preference storage for favorite websites, apps, and locations.
  - Regressions test suite coverage.
- Browser Automation:
  - Keyboard-shortcut bindings (tab navigation, reload, new tab, go back/forward).
  - Active browser page content extraction and local LLM summarization.
  - Regressions test suite coverage.
- Capability Registry:
  - Central registry module detailing all actions, intents, slots, and descriptions in capabilities.py.
  - Expose formatting method to inject this register directly into the LLM system prompt.
  - Implement LLM route_intent classification method to intelligently fallback and choose paths when regex parsing fails.
  - Regressions test suite coverage.
- Hybrid QA routing:
  - Simple QA stays on the local Ollama model.
  - Complex or context-heavy QA can route to Gemini when enabled.
  - Gemini failures fall back to the local model instead of breaking the request.
  - Local secret storage added for non-repo API key handling.
  - Regressions test suite coverage.
- Conversation, Memory, and Autonomy retrieval:
  - QA pipeline now pulls active reminders, alarms, and timers into LLM context.
  - Learned preferences (preferred location, favorite sites, preferred apps, canonical aliases) included in QA context.
  - Broad autonomy preserved: only destructive intents require confirmation.
  - Regressions test suite coverage.
- Better Desktop Automation, app-specific helpers pass:
  - SpotifyHelper: play/pause, next/previous track, volume up/down via keyboard shortcuts.
  - DiscordHelper: mute/unmute (Ctrl+Shift+M), deafen (Ctrl+Shift+D), quick-nav to channel/user (Ctrl+K).
  - SlackHelper: mute/unmute, quick-nav to channel/user (Ctrl+K).
  - BrowserHelper extended: browser_click_control (pywinauto with Ctrl+F fallback), browser_fill_form (JSON or label:value parsing).
  - 13 new intents wired end-to-end: routing → dispatch → helper.
  - 13 new capabilities registered in CapabilityRegistry.
  - Routing conflict between browser_click_control and ui_click_control resolved by ordering patterns correctly.
  - Regressions test suite coverage (161 tests passing).
