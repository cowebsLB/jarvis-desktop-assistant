from __future__ import annotations

import logging
import webbrowser
from datetime import UTC, datetime
from uuid import uuid4

from .actions import ActionExecutor
from .config import Settings
from .history import HistoryEvent, HistoryRecorder
from .intent_router import IntentRouter
from .llm import AssistantLLM
from .models import AssistantRequest, ActionResult, IntentResult, RuntimeState
from .research import WebResearcher
from .response_style import ResponseStyle
from .session import SessionManager
from .speech import MissingSpeechToText, SpeechToText, TextToSpeech
from .state_manager import StateManager, StateTransition
from .weather import WeatherService


LOGGER = logging.getLogger(__name__)


class DesktopAssistant:
    def __init__(
        self,
        settings: Settings,
        router: IntentRouter,
        actions: ActionExecutor,
        stt,
        tts: TextToSpeech,
        llm: AssistantLLM,
        weather: WeatherService,
        history: HistoryRecorder,
        researcher: WebResearcher | None = None,
        hud=None,
    ) -> None:
        self.settings = settings
        self.router = router
        self.actions = actions
        self.stt = stt
        self.tts = tts
        self.llm = llm
        self.weather = weather
        self.history = history
        self.researcher = researcher
        self.hud = hud
        self.state_manager = StateManager(initial_state=RuntimeState.IDLE, on_transition=self._record_state_transition)
        self.session = SessionManager(settings.conversation_followup_seconds)
        self._active_correlation_id: str | None = None
        self._active_conversation_id: str | None = None

        from .productivity import ProductivityManager
        self.productivity = ProductivityManager(on_notification=self._handle_productivity_notification)
        self.productivity.start()

    def _handle_productivity_notification(self, message: str) -> None:
        self.history.append(
            HistoryEvent(
                kind="alert_triggered",
                data={"message": message},
                summary=message,
            )
        )
        self.tts.speak(message)

    def reload_stt(self) -> None:
        self.stt = SpeechToText(self.settings)

    def disable_stt(self, reason: str) -> None:
        self.stt = MissingSpeechToText(reason)

    @property
    def runtime_state(self) -> RuntimeState:
        return self.state_manager.current

    def set_runtime_state(
        self,
        state: RuntimeState,
        *,
        reason: str | None = None,
        correlation_id: str | None = None,
        conversation_id: str | None = None,
    ) -> None:
        if state == RuntimeState.SHUTTING_DOWN:
            self.productivity.stop()
        self.state_manager.transition(
            state,
            reason=reason,
            correlation_id=correlation_id or self._active_correlation_id,
            conversation_id=conversation_id or self._active_conversation_id,
        )
        if self.hud:
            self.hud.on_state_change(state, reason)

    def listen_and_handle(self) -> ActionResult:
        correlation_id = str(uuid4())
        conversation_id = self.session.conversation_id_for_turn()
        self._active_correlation_id = correlation_id
        self._active_conversation_id = conversation_id
        self.set_runtime_state(RuntimeState.TRANSCRIBING, reason="starting transcription")
        try:
            transcript = self.stt.transcribe_once()
        except Exception as exc:
            self.set_runtime_state(RuntimeState.ERROR, reason="speech-to-text startup failure")
            result = ActionResult(
                False,
                str(exc),
                ResponseStyle.stt_unavailable(),
            )
            self.history.append(
                HistoryEvent(
                    kind="request_error",
                    data={"error": str(exc), "stage": "stt_startup"},
                    pinned=True,
                    summary="Speech recognition unavailable during request start.",
                    correlation_id=correlation_id,
                    conversation_id=conversation_id,
                )
            )
            self._speak_and_transition(result)
            return result
        self.set_runtime_state(RuntimeState.UNDERSTANDING, reason="transcript captured")
        if not transcript.text:
            result = ActionResult(
                False,
                "No speech detected.",
                ResponseStyle.no_speech(),
            )
            self.history.append(
                HistoryEvent(
                    kind="request_no_speech",
                    data={
                        "audio_seconds": transcript.audio_seconds,
                        "ended_early": transcript.ended_early,
                    },
                    summary="Wake-triggered request ended without a usable transcript.",
                    correlation_id=correlation_id,
                    conversation_id=conversation_id,
                )
            )
            self._speak_and_transition(result)
            return result

        request = AssistantRequest(
            source="microphone",
            transcript=transcript.text,
            timestamp=datetime.now(UTC),
            audio_seconds=transcript.audio_seconds,
        )
        return self._handle_request(request, correlation_id=correlation_id, conversation_id=conversation_id)

    def handle_text_input(self, text: str, *, source: str = "hud") -> ActionResult:
        correlation_id = str(uuid4())
        conversation_id = self.session.conversation_id_for_turn()
        self._active_correlation_id = correlation_id
        self._active_conversation_id = conversation_id
        self.set_runtime_state(RuntimeState.UNDERSTANDING, reason="text input received")
        request = AssistantRequest(
            transcript=text,
            timestamp=datetime.now(UTC),
            source=source,
            audio_seconds=None,
        )
        return self._handle_request(request, correlation_id=correlation_id, conversation_id=conversation_id)

    def _handle_request(self, request: AssistantRequest, *, correlation_id: str, conversation_id: str) -> ActionResult:
        LOGGER.info("Transcript: %s", request.transcript)
        if self.hud:
            self.hud.on_transcript(request.transcript)
        normalized_followup = self.router.normalize_for_followup(request.transcript)
        confirmation = self.session.consume_confirmation(normalized_followup)
        clarification = None if confirmation else self._consume_clarification(normalized_followup, request.transcript)
        followup = None if confirmation or clarification else self.session.resolve_followup(normalized_followup)
        if confirmation:
            intent = confirmation[1] if confirmation[0] == "confirmed" and confirmation[1] else IntentResult("confirmation_cancelled", 1.0, {})
        elif clarification:
            intent = clarification
        else:
            intent = IntentResult(followup[0], 0.96, followup[1]) if followup else self.router.route(request.transcript)
            if intent.intent == "unsupported":
                LOGGER.info("Regex routing returned unsupported. Trying LLM-based intent routing.")
                llm_intent = self.llm.route_intent(request.transcript)
                if llm_intent:
                    intent = llm_intent
        LOGGER.info("Intent: %s", intent.intent)
        if self.hud:
            self.hud.on_intent(intent.intent, intent.slots)
        self.set_runtime_state(RuntimeState.PLANNING, reason=f"routing intent {intent.intent}")
        self.history.append(
            HistoryEvent(
                kind="request_routed",
                data={
                    "transcript": request.transcript,
                    "audio_seconds": request.audio_seconds,
                    "source": request.source,
                    "intent": intent.intent,
                    "slots": intent.slots,
                },
                pinned=intent.intent in {"unsupported"},
                summary=f"Transcript routed to {intent.intent}.",
                correlation_id=correlation_id,
                conversation_id=conversation_id,
            )
        )

        if intent.intent == "confirmation_cancelled":
            result = ActionResult(True, "Pending action cancelled.", "Very well. Cancelled.")
        elif intent.intent in {"clear_tasks", "clear_timers", "clear_reminders", "clear_alarms"} and intent.slots.get("_confirmed") != "true":
            action_name = intent.intent.replace("_", " ")
            prompt = f"Are you sure you want to {action_name}?"
            self.session.set_confirmation(intent, prompt)
            result = ActionResult(False, f"Pending confirmation to {action_name}.", prompt)
        elif intent.intent == "weather":
            self.set_runtime_state(RuntimeState.EXECUTING, reason="fetching weather")
            summary = self.weather.get_summary(intent.slots.get("location") or None)
            result = ActionResult(True, summary.details, summary.spoken)
        elif intent.intent == "web_search":
            result = self._handle_web_search(intent.slots["query"])
        elif intent.intent == "recall_memory":
            self.set_runtime_state(RuntimeState.EXECUTING, reason="recalling archive notes")
            result = self._handle_archive_recall(intent.slots["query"])
        elif intent.intent == "qa":
            self.set_runtime_state(RuntimeState.EXECUTING, reason="answering question")
            answer = self._answer_question(intent.slots["query"])
            result = ActionResult(True, answer, answer)
        elif intent.intent == "set_timer":
            from .productivity import parse_duration_to_seconds
            duration_sec = parse_duration_to_seconds(intent.slots["duration"], intent.slots["unit"])
            label = f"{intent.slots['duration']} {intent.slots['unit']}"
            self.productivity.add_timer(label, duration_sec)
            msg = f"Timer set for {intent.slots['duration']} {intent.slots['unit']}."
            result = ActionResult(True, msg, msg)
        elif intent.intent == "set_reminder":
            from .productivity import parse_duration_to_seconds
            duration_sec = parse_duration_to_seconds(intent.slots["duration"], intent.slots["unit"])
            self.productivity.add_reminder(intent.slots["text"], duration_sec)
            msg = f"Reminder set: {intent.slots['text']} in {intent.slots['duration']} {intent.slots['unit']}."
            result = ActionResult(True, msg, msg)
        elif intent.intent == "set_alarm":
            h = int(intent.slots["hour"])
            m = int(intent.slots["minute"])
            p = intent.slots["period"]
            self.productivity.add_alarm(h, m, p)
            period_str = f" {p.upper()}" if p else ""
            msg = f"Alarm set for {h:02d}:{m:02d}{period_str}."
            result = ActionResult(True, msg, msg)
        elif intent.intent == "add_task":
            self.productivity.add_task(intent.slots["task"])
            archive = getattr(self.researcher, "archive", None)
            if archive:
                archive.sync_tasks(self.productivity.tasks, getattr(self.researcher, "embedder", None))
            msg = f"Added '{intent.slots['task']}' to your tasks."
            result = ActionResult(True, msg, msg)
        elif intent.intent == "list_tasks":
            tasks = self.productivity.list_tasks()
            if not tasks:
                msg = "Your task list is empty."
            else:
                msg = "Here are your tasks: " + ", ".join(f"{idx+1}. {t}" for idx, t in enumerate(tasks))
            result = ActionResult(True, msg, msg)
        elif intent.intent == "clear_tasks":
            self.productivity.clear_tasks()
            archive = getattr(self.researcher, "archive", None)
            if archive:
                archive.sync_tasks([], getattr(self.researcher, "embedder", None))
            msg = "Task list cleared."
            result = ActionResult(True, msg, msg)
        elif intent.intent == "clear_timers":
            self.productivity.clear_timers()
            msg = "Timers cleared."
            result = ActionResult(True, msg, msg)
        elif intent.intent == "clear_reminders":
            self.productivity.clear_reminders()
            msg = "Reminders cleared."
            result = ActionResult(True, msg, msg)
        elif intent.intent == "clear_alarms":
            self.productivity.clear_alarms()
            msg = "Alarms cleared."
            result = ActionResult(True, msg, msg)
        elif intent.intent == "take_note":
            from pathlib import Path
            note_text = intent.slots["text"]
            notes_dir = Path.home() / ".desktop_voice_assistant"
            notes_dir.mkdir(parents=True, exist_ok=True)
            notes_file = notes_dir / "quick-notes.md"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with notes_file.open("a", encoding="utf-8") as f:
                f.write(f"## {timestamp}\n\n{note_text}\n\n")
            msg = f"Note saved: {note_text}"
            result = ActionResult(True, msg, msg)
        elif intent.intent == "browser_summarize":
            self.set_runtime_state(RuntimeState.EXECUTING, reason="scraping active page content")
            page_text = self.actions._get_active_page_text()
            if not page_text:
                result = ActionResult(False, "Could not capture page content. Ensure browser window is focused.", "I could not capture any web page content to summarize.")
            else:
                self.set_runtime_state(RuntimeState.EXECUTING, reason="summarizing page content")
                truncated_text = page_text[:4000]
                prompt = "Summarize the active web page content compactly:"
                summary = self.llm.answer_with_context(prompt, truncated_text)
                result = ActionResult(True, summary, summary)
        elif intent.intent == "open_target":
            result = self._handle_open_target(intent)
        elif intent.intent == "unsupported":
            result = self._handle_unsupported(request.transcript)
        else:
            self.set_runtime_state(RuntimeState.EXECUTING, reason=f"executing intent {intent.intent}")
            result = self.actions.execute(intent)

        # Save to conversational turn memory
        self.actions.memory.add_turn(request.transcript, result.spoken_reply or result.message, self.llm)
        archive = getattr(self.researcher, "archive", None)
        if archive:
            turn_id = archive.add_conversation_turn(request.transcript, result.spoken_reply or result.message)
            embedder = getattr(self.researcher, "embedder", None)
            if embedder:
                vector = embedder.embed(f"User: {request.transcript}\nJarvis: {result.spoken_reply or result.message}")
                if vector:
                    archive.store_conversation_embedding(turn_id, vector)

        self._update_session(intent, result)

        self.history.append(
            HistoryEvent(
                kind="request_completed",
                data={
                    "intent": intent.intent,
                    "success": result.success,
                    "message": result.message,
                    "spoken_reply": result.spoken_reply,
                },
                pinned=not result.success,
                summary=result.message,
                correlation_id=correlation_id,
                conversation_id=conversation_id,
            )
        )
        self._speak_and_transition(result)
        return result

    def _answer_question(self, query: str) -> str:
        # Check local database knowledge first (unifies research, tasks, and conversation history)
        archive = getattr(self.researcher, "archive", None)
        if archive:
            local_hits = archive.search_local(
                query,
                limit=self.settings.archive_recall_limit,
                embedder=getattr(self.researcher, "embedder", None)
            )
            if local_hits:
                context_blocks = []
                for hit in local_hits:
                    if hit["type"] == "research":
                        context_blocks.append(f"[Stored Research] Title: {hit['title']}\nContent: {hit['content'][:1500]}")
                    elif hit["type"] == "task":
                        context_blocks.append(f"[Active Task] Task Description: {hit['content']}")
                    elif hit["type"] == "conversation":
                        context_blocks.append(f"[Past Conversation Turn]\n{hit['content']}")
                
                context = "\n\n---\n\n".join(context_blocks)
                prompt = (
                    f"Question: {query}\n\n"
                    "Answer the question concisely based only on the provided local records context. "
                    "If the records show a task or past conversation, summarize or respond directly referencing that local context.\n\n"
                    f"Local Records Context:\n{context}"
                )
                return self.llm.answer_with_context(query, prompt)

        # Fallback to recent conversation turn context
        history_context = self.actions.memory.get_turns_context()
        if history_context:
            return self.llm.answer_with_context(query, history_context)

        return self.llm.answer(query)

    def _handle_web_search(self, query: str) -> ActionResult:
        if not self.settings.web_search_enabled or not self.researcher:
            return ActionResult(False, "Web research is disabled.", "Web research is disabled right now.")
        research = self.researcher.research(query)
        message = research.answer
        spoken = research.spoken
        if self.settings.web_open_after_answer and research.sources:
            top_source = research.sources[0]
            webbrowser.open(top_source.url)
            message = f"{message} Opened top source: {top_source.title}."
            spoken = f"{spoken} I've opened the top source as well."
        return ActionResult(
            True,
            message,
            spoken,
            sources=research.sources,
        )

    def _handle_archive_recall(self, query: str) -> ActionResult:
        if not self.researcher:
            return ActionResult(False, "Archive recall is unavailable.", ResponseStyle.archive_empty(query))
        recall = self.researcher.recall(query, limit=self.settings.archive_recall_limit)
        if not recall:
            return ActionResult(False, "No stored research found.", ResponseStyle.archive_empty(query))
        return ActionResult(True, recall.answer, recall.spoken)

    def _build_unsupported_feedback(self, transcript: str) -> ActionResult:
        heard = transcript.strip()
        lowered = heard.lower()

        app_names = set(self.settings.app_allowlist) | {"calculator", "chrome", "notepad", "settings"}
        for app_name in sorted(app_names):
            if app_name in lowered:
                spoken = f"I heard {heard}. If you want me to launch it, say open {app_name}."
                return ActionResult(False, f"Likely app request for {app_name} was not phrased as a supported action.", spoken)

        if any(term in lowered for term in ("search", "google", "look up", "find")):
            spoken = (
                f"I heard {heard}. Try saying search the web for followed by what you want me to look up."
            )
            return ActionResult(False, "Search request was not in a supported form.", spoken)

        spoken = (
            f"I heard {heard}. I can currently open apps, folders, and files, calculate expressions, answer questions, get weather, and search the web."
        )
        return ActionResult(False, "Request is outside the currently supported commands.", spoken)

    def _handle_unsupported(self, transcript: str) -> ActionResult:
        normalized = self.router.normalize_for_followup(transcript)
        if normalized in {"open it", "open that", "open the source", "open"}:
            self.session.set_clarification("open_target", "target", "What would you like me to open?")
            self.set_runtime_state(RuntimeState.CLARIFYING, reason="missing open target context")
            return ActionResult(False, "Clarification requested.", "What would you like me to open?")
        if normalized in {"summarize that", "summarize it", "summarize"}:
            self.session.set_clarification("recall_memory", "query", "What would you like me to summarize?")
            self.set_runtime_state(RuntimeState.CLARIFYING, reason="missing summary target context")
            return ActionResult(False, "Clarification requested.", "What would you like me to summarize?")
        return self._build_unsupported_feedback(transcript)

    def _consume_clarification(self, normalized_text: str, raw_text: str) -> IntentResult | None:
        if normalized_text in {"yes", "yeah", "yep", "confirm", "do it", "go ahead", "no", "nope", "cancel", "stop"}:
            return None
        pending = self.session.snapshot.pending_clarification
        if pending is None:
            return None
        self.set_runtime_state(RuntimeState.UNDERSTANDING, reason="clarification received")
        return self.session.consume_clarification(raw_text)

    def _handle_open_target(self, intent: IntentResult) -> ActionResult:
        if intent.slots.get("_confirmed") == "true":
            confirmed_slots = dict(intent.slots)
            confirmed_slots.pop("_confirmed", None)
            confirmed_intent = IntentResult(intent.intent, intent.confidence, confirmed_slots)
            self.set_runtime_state(RuntimeState.EXECUTING, reason=f"executing confirmed intent {intent.intent}")
            return self.actions.execute(confirmed_intent)

        normalized_target = self.router.normalize_for_followup(intent.slots["target"])
        if normalized_target in {"it", "that", "the source", "the first source"}:
            if not self.session.snapshot.last_sources and not self.session.snapshot.last_open_target:
                self.session.set_clarification("open_target", "target", "What would you like me to open?")
                self.set_runtime_state(RuntimeState.CLARIFYING, reason="missing open target context")
                return ActionResult(False, "Clarification requested.", "What would you like me to open?")
        preview = self.actions.preview_open_target(intent.slots["target"])
        if preview.fuzzy_match:
            confirmed_intent = IntentResult("open_target", 0.95, {"target": preview.fuzzy_match})
            self.session.set_confirmation(
                confirmed_intent,
                f"I heard {preview.requested_target}. Do you want {preview.fuzzy_match}?",
            )
            self.set_runtime_state(RuntimeState.AWAITING_CONFIRMATION, reason="confirm fuzzy app match")
            return ActionResult(
                False,
                f"Pending confirmation for {preview.fuzzy_match}.",
                f"I heard {preview.requested_target}. Do you want {preview.fuzzy_match}?",
            )
        if self.settings.confirmation_policy == "always" and preview.launchable:
            confirmed_intent = IntentResult("open_target", intent.confidence, {"target": preview.resolved_target})
            prompt = f"Confirm opening {preview.resolved_target}?"
            self.session.set_confirmation(confirmed_intent, prompt)
            self.set_runtime_state(RuntimeState.AWAITING_CONFIRMATION, reason="confirmation policy requires approval")
            return ActionResult(
                False,
                f"Pending confirmation for {preview.resolved_target}.",
                prompt,
            )
        self.set_runtime_state(RuntimeState.EXECUTING, reason=f"executing intent {intent.intent}")
        return self.actions.execute(intent)

    def _speak_and_transition(self, result: ActionResult) -> None:
        if self.hud:
            self.hud.on_result(result.spoken_reply or result.message, success=result.success, sources=result.sources)
        if result.spoken_reply:
            self.set_runtime_state(RuntimeState.SPEAKING, reason="speaking reply")
            self.tts.speak(result.spoken_reply)
        if self.session.snapshot.pending_confirmation is not None:
            self.set_runtime_state(RuntimeState.AWAITING_CONFIRMATION, reason="waiting for confirmation response")
            return
        if self.session.snapshot.pending_clarification is not None:
            self.set_runtime_state(RuntimeState.CLARIFYING, reason="waiting for clarification response")
            return
        self.set_runtime_state(RuntimeState.AWAITING_FOLLOWUP, reason="request completed")

    def _record_state_transition(self, transition: StateTransition) -> None:
        self.history.append(
            HistoryEvent(
                kind="state_transition",
                data={
                    "reason": transition.reason,
                    "state_from": transition.previous.value,
                    "state_to": transition.current.value,
                },
                summary=f"State changed from {transition.previous.value} to {transition.current.value}.",
                correlation_id=transition.correlation_id,
                conversation_id=transition.conversation_id,
                state_from=transition.previous.value,
                state_to=transition.current.value,
            )
        )

    def _update_session(self, intent: IntentResult, result: ActionResult) -> None:
        tracked_query = intent.slots.get("query") or intent.slots.get("target")
        self.session.mark_result(
            intent=intent.intent,
            query=tracked_query,
            open_target=result.opened_target,
            sources=result.sources,
        )
