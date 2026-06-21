from __future__ import annotations

import logging
import math
import queue
import threading
import webbrowser
import tkinter as tk
from typing import Any
from PIL import Image, ImageDraw, ImageTk

from .config import Settings
from .models import RuntimeState, ResearchSource

LOGGER = logging.getLogger(__name__)

STATE_COLORS = {
    # state: (primary_hex, glow_hex)
    "booting": ("#38BDF8", "#0284C7"),
    "idle": ("#38BDF8", "#0284C7"),
    "wake_listening": ("#38BDF8", "#0284C7"),
    "capturing_command": ("#22C55E", "#15803D"),
    "transcribing": ("#22C55E", "#15803D"),
    "understanding": ("#F59E0B", "#B45309"),
    "clarifying": ("#F59E0B", "#B45309"),
    "planning": ("#F59E0B", "#B45309"),
    "researching": ("#A855F7", "#7E22CE"),
    "fetching_sources": ("#A855F7", "#7E22CE"),
    "ranking_sources": ("#A855F7", "#7E22CE"),
    "summarizing_sources": ("#A855F7", "#7E22CE"),
    "archiving_sources": ("#A855F7", "#7E22CE"),
    "awaiting_confirmation": ("#F97316", "#C2410C"),
    "executing": ("#A855F7", "#7E22CE"),
    "speaking": ("#10B981", "#047857"),
    "awaiting_followup": ("#10B981", "#047857"),
    "error": ("#EF4444", "#B91C1C"),
    "shutting_down": ("#64748B", "#475569"),
    "suspended": ("#64748B", "#475569"),
}


class FloatingHud:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.queue: queue.Queue = queue.Queue()
        self.root: tk.Tk | None = None
        self.thread: threading.Thread | None = None
        self.on_submit_text = None
        self._enabled = settings.hud_enabled
        self._stopped = False

        # State data
        self.state: RuntimeState = RuntimeState.BOOTING
        self.reason: str | None = None
        self.transcript: str = ""
        self.intent: str = ""
        self.slots: dict[str, str] = {}
        self.reply: str = ""
        self.sources: list[ResearchSource] = []
        self.history_events: list[dict[str, Any]] = []

        # UI state
        self.expanded: bool = True
        self.drag_data: dict[str, int] = {"x": 0, "y": 0}
        self.pulse_phase: float = 0.0
        self.wake_pulse_active: bool = False
        self.wake_pulse_radius: float = 0.0
        self.orb_items: dict[str, Any] = {}

        # Load initial history
        self.history_events = self._load_recent_history()

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self._stopped = False
        self.thread = threading.Thread(target=self._run_gui, daemon=True, name="hud-gui-thread")
        self.thread.start()

    def stop(self) -> None:
        self._stopped = True
        if self.root:
            self.queue.put(self.root.destroy)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.settings.hud_enabled = enabled
        if self.root:
            self.queue.put(lambda: self._ui_set_enabled(enabled))

    def wake_detected(self) -> None:
        self.queue.put(self._ui_wake_detected)

    def on_state_change(self, state: RuntimeState, reason: str | None = None) -> None:
        self.queue.put(lambda: self._ui_state_change(state, reason))

    def on_transcript(self, transcript: str) -> None:
        self.queue.put(lambda: self._ui_transcript(transcript))

    def on_intent(self, intent: str, slots: dict[str, str]) -> None:
        self.queue.put(lambda: self._ui_intent(intent, slots))

    def on_result(self, reply: str | None, *, success: bool, sources=None) -> None:
        self.queue.put(lambda: self._ui_result(reply, success, sources))

    def on_history_event(self, record: dict[str, Any]) -> None:
        self.queue.put(lambda: self._ui_history_event(record))

    # --- Thread-Safe UI Update Helpers ---

    def _ui_wake_detected(self) -> None:
        self.wake_pulse_active = True
        self.wake_pulse_radius = 45.0

    def _ui_state_change(self, state: RuntimeState, reason: str | None) -> None:
        self.state = state
        self.reason = reason
        # Auto-expand detail view when active work starts
        state_val = state.value if hasattr(state, "value") else str(state)
        if state_val not in ["idle", "wake_listening", "suspended"] and not self.expanded:
            self.expanded = True
            self._update_window_size()
        self._refresh_hud()

    def _ui_transcript(self, transcript: str) -> None:
        self.transcript = transcript
        self._refresh_hud()

    def _ui_intent(self, intent: str, slots: dict[str, str]) -> None:
        self.intent = intent
        self.slots = slots
        self._refresh_hud()

    def _ui_result(self, reply: str | None, success: bool, sources=None) -> None:
        self.reply = reply or ""
        self.sources = sources or []
        self._refresh_hud()

    def _ui_history_event(self, record: dict[str, Any]) -> None:
        self.history_events.append(record)
        if len(self.history_events) > 8:
            self.history_events.pop(0)
        self._refresh_history_ui()

    def _ui_set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not self.root:
            return
        if enabled:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
        else:
            self.root.withdraw()

    # --- Tkinter GUI Implementation ---

    def _run_gui(self) -> None:
        self.root = tk.Tk()
        self.root.title("Jarvis HUD")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.96)
        self.root.configure(bg="#0B0F19")

        # Geometry
        x = self.settings.hud_position_x
        y = self.settings.hud_position_y
        if x is None or y is None:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = screen_w - 380
            y = screen_h - 600
            self.settings.hud_position_x = x
            self.settings.hud_position_y = y
            self.settings.save()

        # Build UI Elements
        self._create_widgets()
        self._update_window_size()

        # Start loops
        self._check_queue()
        self.animate_orb()
        self._ui_set_enabled(self._enabled)

        self.root.mainloop()
        self.root = None
        self.thread = None

    def _create_card(self, parent: tk.Widget, title: str, title_color: str) -> tuple[tk.Frame, tk.Frame]:
        card = tk.Frame(
            parent,
            bg="#131E35",
            highlightthickness=1,
            highlightbackground="#1E2E4A",
            bd=0
        )
        title_lbl = tk.Label(
            card,
            text=title,
            font=("Consolas", 8, "bold"),
            fg=title_color,
            bg="#131E35",
            anchor="w"
        )
        title_lbl.pack(fill="x", padx=8, pady=(4, 2))
        sep = tk.Frame(card, height=1, bg="#1E2E4A")
        sep.pack(fill="x", padx=6, pady=(0, 4))
        inner = tk.Frame(card, bg="#131E35")
        inner.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        return card, inner

    def _create_widgets(self) -> None:
        if not self.root:
            return

        # Top Bar Frame (Contains Orb, Status, Chevron)
        self.top_frame = tk.Frame(self.root, bg="#0B0F19", cursor="fleur")
        self.top_frame.pack(fill="x", side="top")
        self.top_frame.bind("<Button-1>", self._on_drag_start)
        self.top_frame.bind("<B1-Motion>", self._on_drag_motion)
        self.top_frame.bind("<ButtonRelease-1>", self._on_drag_release)

        # Glowing Orb Canvas
        self.canvas = tk.Canvas(self.top_frame, width=60, height=60, bg="#0B0F19", highlightthickness=0)
        self.canvas.pack(side="left", padx=5, pady=5)
        self.canvas.bind("<Button-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_release)

        # Initialize the persistent canvas items to avoid recreate stuttering
        self._initialize_orb_graphics()

        # Status Label
        self.status_lbl = tk.Label(
            self.top_frame,
            text="Jarvis: Idle",
            font=("Segoe UI", 10, "bold"),
            fg="#38BDF8",
            bg="#0B0F19",
            anchor="w"
        )
        self.status_lbl.pack(side="left", fill="x", expand=True, padx=5)
        self.status_lbl.bind("<Button-1>", self._on_drag_start)
        self.status_lbl.bind("<B1-Motion>", self._on_drag_motion)
        self.status_lbl.bind("<ButtonRelease-1>", self._on_drag_release)

        # Expand/Collapse Chevron Button
        self.expand_btn = tk.Button(
            self.top_frame,
            text="▲",
            font=("Segoe UI", 9, "bold"),
            fg="#64748B",
            bg="#0B0F19",
            activeforeground="#F1F5F9",
            activebackground="#131E35",
            bd=0,
            relief="flat",
            padx=10,
            command=self._toggle_expand
        )
        self.expand_btn.pack(side="right", fill="y", padx=5)
        self.expand_btn.bind("<Enter>", lambda e: self.expand_btn.config(fg="#F1F5F9", bg="#131E35"))
        self.expand_btn.bind("<Leave>", lambda e: self.expand_btn.config(fg="#64748B", bg="#0B0F19"))

        # Details Panel Container (Packed when expanded)
        self.details_frame = tk.Frame(self.root, bg="#0B0F19")
        
        # 1. Transcript Card
        self.transcript_card, self.transcript_inner = self._create_card(self.details_frame, "[ USER COMMAND ]", "#38BDF8")
        self.transcript_card.pack(fill="x", pady=4, padx=2)
        
        self.transcript_lbl = tk.Label(
            self.transcript_inner,
            text="(Waiting for command...)",
            font=("Segoe UI", 9, "italic"),
            fg="#E2E8F0",
            bg="#131E35",
            justify="left",
            anchor="w",
            wraplength=320
        )
        self.transcript_lbl.pack(fill="x", pady=2)

        self.intent_lbl = tk.Label(
            self.transcript_inner,
            text="INTENT: None",
            font=("Consolas", 8, "bold"),
            fg="#94A3B8",
            bg="#131E35",
            anchor="w"
        )
        self.intent_lbl.pack(fill="x", pady=(4, 0))

        # 2. Plan & Progress Section
        self.steps_card, self.steps_inner_frame = self._create_card(self.details_frame, "[ PROCESS RUNTIME ]", "#38BDF8")
        self.steps_card.pack(fill="x", pady=4, padx=2)

        # 3. Citations Section
        self.citations_card, self.citations_inner_frame = self._create_card(self.details_frame, "[ RESEARCH SOURCES ]", "#A855F7")
        self.citations_card.pack(fill="x", pady=4, padx=2)

        # 4. Confirmation Panel (Yes / No + typed follow-up)
        self.confirmation_card, self.confirmation_inner = self._create_card(self.details_frame, "[ USER CONFIRMATION ]", "#F97316")
        
        self.confirmation_lbl = tk.Label(
            self.confirmation_inner,
            text="Are you sure?",
            font=("Segoe UI", 9),
            fg="#F1F5F9",
            bg="#131E35",
            wraplength=320,
            justify="center"
        )
        self.confirmation_lbl.pack(fill="x", pady=4)
        
        self.buttons_frame = tk.Frame(self.confirmation_inner, bg="#131E35")
        self.buttons_frame.pack(pady=4)
        
        self.yes_btn = tk.Button(
            self.buttons_frame,
            text="Confirm [Yes]",
            font=("Segoe UI", 9, "bold"),
            fg="#F1F5F9",
            bg="#22C55E",
            activebackground="#16A34A",
            activeforeground="#F1F5F9",
            bd=0,
            width=14,
            pady=4,
            command=self._confirm_yes
        )
        self.yes_btn.pack(side="left", padx=10)
        
        self.no_btn = tk.Button(
            self.buttons_frame,
            text="Cancel [No]",
            font=("Segoe UI", 9, "bold"),
            fg="#F1F5F9",
            bg="#EF4444",
            activebackground="#DC2626",
            activeforeground="#F1F5F9",
            bd=0,
            width=14,
            pady=4,
            command=self._confirm_no
        )
        self.no_btn.pack(side="left", padx=10)

        # 5. Recent History Section
        self.history_card, self.history_inner_frame = self._create_card(self.details_frame, "[ SYSTEM LOGS ]", "#10B981")
        self.history_card.pack(fill="x", pady=4, padx=2)

        # 6. Text Follow-up Entry Console
        self.entry_card, self.entry_inner = self._create_card(self.details_frame, "[ INTERACTION CONSOLE ]", "#38BDF8")
        self.entry_card.pack(fill="x", side="bottom", pady=4, padx=2)
        
        self.input_entry = tk.Entry(
            self.entry_inner,
            font=("Consolas", 9),
            fg="#F1F5F9",
            bg="#0B0F19",
            insertbackground="#F1F5F9",
            bd=0,
            highlightthickness=1,
            highlightbackground="#1E2E4A",
            highlightcolor="#38BDF8"
        )
        self.input_entry.pack(fill="x", ipady=4, padx=2, pady=2)
        self.input_entry.bind("<Return>", self._submit_typed_text)
        
        # Add a subtle placeholder
        self.input_entry.insert(0, "Type follow-up & press Enter...")
        self.input_entry.bind("<FocusIn>", self._clear_placeholder)
        self.input_entry.bind("<FocusOut>", self._add_placeholder)

        # First paint
        self._refresh_hud()
        self._refresh_history_ui()

    def _toggle_expand(self) -> None:
        self.expanded = not self.expanded
        self._update_window_size()

    def _update_window_size(self) -> None:
        if not self.root:
            return
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        if self.expanded:
            self.details_frame.pack(fill="both", expand=True, padx=8, pady=5)
            self.root.geometry(f"360x560+{x}+{y}")
            self.expand_btn.config(text="▲")
        else:
            self.details_frame.pack_forget()
            self.root.geometry(f"280x60+{x}+{y}")
            self.expand_btn.config(text="▼")

    def _refresh_hud(self) -> None:
        if not self.root:
            return
        if not self._enabled:
            return

        state_val = self.state.value if hasattr(self.state, "value") else str(self.state)
        # Update Status Text
        status_text = f"Jarvis: {state_val.replace('_', ' ').title()}"
        self.status_lbl.config(text=status_text)
        
        # Apply theme color to Status text based on state
        state_color = STATE_COLORS.get(state_val, ("#38BDF8", "#0284C7"))[0]
        self.status_lbl.config(fg=state_color)

        # Update Transcript Bubble
        if self.transcript:
            self.transcript_lbl.config(text=self.transcript, font=("Segoe UI", 9, "normal"))
        else:
            self.transcript_lbl.config(text="(Waiting for command...)", font=("Segoe UI", 9, "italic"))

        # Update Intent Label
        intent_text = f"Intent: {self.intent.replace('_', ' ').title() if self.intent else 'None'}"
        if self.slots:
            slots_str = ", ".join(f"{k}={v}" for k, v in self.slots.items())
            intent_text += f" ({slots_str})"
        self.intent_lbl.config(text=intent_text)

        # Update planned steps list
        self._refresh_progress_ui()

        # Update citations
        self._refresh_citations_ui()

        # Update confirmation panel
        self._refresh_confirmation_ui()

    def _refresh_progress_ui(self) -> None:
        if not self.root:
            return
        if not self._enabled:
            return
        for w in self.steps_inner_frame.winfo_children():
            w.destroy()

        steps = self._get_steps_for_state()
        for label_text, status in steps:
            icon = " "
            status_text = "PENDING"
            color = "#64748B"  # pending gray
            
            if status == "active":
                color = "#38BDF8"  # active sky blue
                status_text = "RUNNING"
                icon = "▶"
            elif status == "done":
                color = "#E2E8F0"  # done text
                status_text = "DONE"
                icon = "✓"

            left_part = f"{icon} {label_text} "
            dot_count = max(1, 30 - len(left_part))
            full_line = f"{left_part}{'.' * dot_count} [{status_text}]"

            lbl = tk.Label(
                self.steps_inner_frame,
                text=full_line,
                font=("Consolas", 8, "bold" if status == "active" else "normal"),
                fg=color,
                bg="#131E35",
                anchor="w",
                justify="left"
            )
            lbl.pack(fill="x", pady=1)

    def _get_steps_for_state(self) -> list[tuple[str, str]]:
        state_val = self.state.value if hasattr(self.state, "value") else str(self.state)
        
        # Decide status mapping
        capture_status = "pending"
        routing_status = "pending"
        exec_status = "pending"
        speak_status = "pending"

        if state_val in ["capturing_command", "transcribing"]:
            capture_status = "active"
        elif state_val in ["understanding", "planning", "clarifying", "researching", "fetching_sources", "ranking_sources", "summarizing_sources", "archiving_sources", "awaiting_confirmation", "executing", "speaking", "awaiting_followup", "idle"]:
            capture_status = "done"

        if state_val in ["understanding", "planning"]:
            routing_status = "active"
        elif state_val in ["clarifying", "researching", "fetching_sources", "ranking_sources", "summarizing_sources", "archiving_sources", "awaiting_confirmation", "executing", "speaking", "awaiting_followup"]:
            routing_status = "done"

        is_research = state_val in ["researching", "fetching_sources", "ranking_sources", "summarizing_sources", "archiving_sources"] or (self.intent in ["web_search", "qa"] and state_val != "idle")
        
        if state_val in ["executing", "researching", "fetching_sources", "ranking_sources", "summarizing_sources", "archiving_sources", "clarifying", "awaiting_confirmation"]:
            exec_status = "active"
        elif state_val in ["speaking", "awaiting_followup"]:
            exec_status = "done"

        if state_val in ["speaking"]:
            speak_status = "active"
        elif state_val in ["awaiting_followup"]:
            speak_status = "done"

        steps = [
            ("Capture Speech", capture_status),
            ("Analyze Intent", routing_status),
        ]

        if is_research:
            steps.append(("Web Search Initiated", "done" if state_val != "researching" else "active"))
            steps.append(("Fetch Web Pages", "active" if state_val == "fetching_sources" else ("done" if state_val in ["ranking_sources", "summarizing_sources", "archiving_sources", "speaking", "awaiting_followup"] else "pending")))
            steps.append(("Rank & Extract Evidence", "active" if state_val == "ranking_sources" else ("done" if state_val in ["summarizing_sources", "archiving_sources", "speaking", "awaiting_followup"] else "pending")))
            steps.append(("Summarize Findings", "active" if state_val == "summarizing_sources" else ("done" if state_val in ["archiving_sources", "speaking", "awaiting_followup"] else "pending")))
        else:
            steps.append(("Execute Desktop Action", exec_status))

        steps.append(("Speak Response", speak_status))
        return steps

    def _refresh_citations_ui(self) -> None:
        if not self.root:
            return
        if not self._enabled:
            return
        for w in self.citations_inner_frame.winfo_children():
            w.destroy()

        if not self.sources:
            lbl = tk.Label(
                self.citations_inner_frame,
                text="No research sources cited for this query.",
                font=("Consolas", 8, "italic"),
                fg="#64748B",
                bg="#131E35",
                anchor="w"
            )
            lbl.pack(fill="x", pady=4)
            return

        for idx, src in enumerate(self.sources[:3]):
            title = src.title if hasattr(src, "title") else src.get("title", f"Source {idx+1}")
            url = src.url if hasattr(src, "url") else src.get("url", "#")
            
            lbl = tk.Label(
                self.citations_inner_frame,
                text=f"[{idx+1}] {title}",
                font=("Consolas", 8),
                fg="#D8B4FE",  # Lavender/Purple links
                bg="#131E35",
                cursor="hand2",
                anchor="w",
                justify="left",
                wraplength=310
            )
            lbl.pack(fill="x", pady=2)
            self._bind_clickable_link(lbl, url)

    def _bind_clickable_link(self, label: tk.Label, url: str) -> None:
        label.bind("<Button-1>", lambda e: webbrowser.open(url))
        label.bind("<Enter>", lambda e: label.config(font=("Consolas", 8, "underline"), fg="#F472B6"))  # Pink glow highlight
        label.bind("<Leave>", lambda e: label.config(font=("Consolas", 8), fg="#D8B4FE"))

    def _refresh_confirmation_ui(self) -> None:
        state_val = self.state.value if hasattr(self.state, "value") else str(self.state)
        if state_val in ["awaiting_confirmation", "clarifying"]:
            self.confirmation_card.pack(fill="x", pady=4, padx=2)
            prompt = self.reason or "Jarvis requires confirmation for this action."
            self.confirmation_lbl.config(text=prompt)
        else:
            self.confirmation_card.pack_forget()

    def _refresh_history_ui(self) -> None:
        if not self.root:
            return
        if not self._enabled:
            return
        for w in self.history_inner_frame.winfo_children():
            w.destroy()

        if not self.history_events:
            lbl = tk.Label(
                self.history_inner_frame,
                text="No recent assistant logs found.",
                font=("Consolas", 8, "italic"),
                fg="#64748B",
                bg="#131E35",
                anchor="w"
            )
            lbl.pack(fill="x", pady=4)
            return

        for record in reversed(self.history_events[-4:]):
            summary = record.get("summary") or record.get("kind", "Interaction event")
            lbl = tk.Label(
                self.history_inner_frame,
                text=f"» {summary}",
                font=("Consolas", 8),
                fg="#34D399",  # Mint green
                bg="#131E35",
                anchor="w",
                justify="left",
                wraplength=310
            )
            lbl.pack(fill="x", pady=1)

    # --- Actions Handling ---

    def _confirm_yes(self) -> None:
        if self.on_submit_text:
            self.on_submit_text("yes")

    def _confirm_no(self) -> None:
        if self.on_submit_text:
            self.on_submit_text("no")

    def _submit_typed_text(self, event: tk.Event) -> None:
        text = self.input_entry.get().strip()
        if not text or text == "Type follow-up & press Enter...":
            return
        self.input_entry.delete(0, tk.END)
        if self.on_submit_text:
            self.on_submit_text(text)

    def _clear_placeholder(self, event: tk.Event) -> None:
        if self.input_entry.get() == "Type follow-up & press Enter...":
            self.input_entry.delete(0, tk.END)
    def _add_placeholder(self, event: tk.Event) -> None:
        if not self.input_entry.get():
            self.input_entry.insert(0, "Type follow-up & press Enter...")

    # --- Glowing Orb Animation ---

    def _hex_to_rgba(self, hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
        hex_str = hex_str.lstrip("#")
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (r, g, b, alpha)

    def _initialize_orb_graphics(self) -> None:
        self.canvas.delete("all")
        self.orb_image_item = self.canvas.create_image(30, 30, anchor="center", tags="orb_img")
        self.orb_photo = None

    def animate_orb(self) -> None:
        if not self.root:
            return

        self.pulse_phase += 0.03
        state_val = self.state.value if hasattr(self.state, "value") else str(self.state)
        primary_hex, glow_hex = STATE_COLORS.get(state_val, ("#38BDF8", "#0284C7"))

        if state_val in [
            "capturing_command", "transcribing", "understanding", "planning",
            "researching", "fetching_sources", "ranking_sources", "summarizing_sources",
            "archiving_sources", "executing", "speaking"
        ]:
            scale = 1.0 + 0.15 * math.sin(self.pulse_phase * 2.5)
            spin_multiplier = 2.5
        else:
            scale = 1.0 + 0.06 * math.sin(self.pulse_phase)
            spin_multiplier = 1.0

        cx, cy = 90, 90
        r_base = 27

        # Create transparent base image (scaled to 180x180 for 3x supersampling)
        img = Image.new("RGBA", (180, 180), (0, 0, 0, 0))

        primary_rgba = self._hex_to_rgba(primary_hex, 255)
        glow_rgba = self._hex_to_rgba(glow_hex, 255)

        # Compositing drawing helpers
        def draw_translucent_ellipse(image, center, radius, fill_color):
            if fill_color[3] == 0:
                return image
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            cx, cy = center
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=fill_color)
            return Image.alpha_composite(image, overlay)

        def draw_translucent_arc(image, center, radius, start_angle, end_angle, outline_color, width):
            if outline_color[3] == 0:
                return image
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            cx, cy = center
            draw.arc([cx - radius, cy - radius, cx + radius, cy + radius], start_angle, end_angle, fill=outline_color, width=width)
            return Image.alpha_composite(image, overlay)

        def draw_translucent_line(image, coords, fill_color, width):
            if fill_color[3] == 0:
                return image
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            draw.line(coords, fill=fill_color, width=width)
            return Image.alpha_composite(image, overlay)

        # 1. Update glow rings (morphing outer rings)
        for i in range(3):
            r = (r_base + (3 - i) * 10.5) * scale
            alpha = int((i + 1) * 35)
            glow_color = (glow_rgba[0], glow_rgba[1], glow_rgba[2], alpha)
            img = draw_translucent_ellipse(img, (cx, cy), r, glow_color)

        # 2. Dotted crosshair ring
        r_cross = 73.5 * scale
        crosshair_rgba = (glow_rgba[0], glow_rgba[1], glow_rgba[2], 120)
        for angle in range(0, 360, 20):
            img = draw_translucent_arc(img, (cx, cy), r_cross, angle, angle + 8, crosshair_rgba, width=3)

        # 3. Spinning Arcs Ring 1 (Clockwise)
        r_ring1 = 67.5 * scale
        angle_offset1 = (self.pulse_phase * 35.0 * spin_multiplier) % 360
        ring1_rgba = (primary_rgba[0], primary_rgba[1], primary_rgba[2], 200)
        for idx in range(2):
            start_angle = angle_offset1 + (idx * 180)
            img = draw_translucent_arc(img, (cx, cy), r_ring1, start_angle, start_angle + 80, ring1_rgba, width=5)

        # 4. Spinning Arcs Ring 2 (Counter-Clockwise)
        r_ring2 = 52.5 * scale
        angle_offset2 = (360 - (self.pulse_phase * 55.0 * spin_multiplier)) % 360
        ring2_rgba = (glow_rgba[0], glow_rgba[1], glow_rgba[2], 180)
        for idx in range(2):
            start_angle = angle_offset2 + (idx * 180)
            img = draw_translucent_arc(img, (cx, cy), r_ring2, start_angle, start_angle + 100, ring2_rgba, width=3)

        # 5. Corner Target Brackets
        bracket_rgba = (primary_rgba[0], primary_rgba[1], primary_rgba[2], 220) if state_val != "idle" else (71, 85, 105, 180)
        b_len = 18
        img = draw_translucent_line(img, [(15, 15 + b_len), (15, 15), (15 + b_len, 15)], bracket_rgba, width=3)
        img = draw_translucent_line(img, [(165 - b_len, 15), (165, 15), (165, 15 + b_len)], bracket_rgba, width=3)
        img = draw_translucent_line(img, [(15, 165 - b_len), (15, 165), (15 + b_len, 165)], bracket_rgba, width=3)
        img = draw_translucent_line(img, [(165 - b_len, 165), (165, 165), (165, 165 - b_len)], bracket_rgba, width=3)

        # 6. Solid Core Center Orb
        core_rgba = (primary_rgba[0], primary_rgba[1], primary_rgba[2], 255)
        img = draw_translucent_ellipse(img, (cx, cy), r_base * scale, core_rgba)

        # 7. Wake Pulse
        if self.wake_pulse_active:
            self.wake_pulse_radius += 6.0
            if self.wake_pulse_radius > 180:
                self.wake_pulse_active = False
            else:
                fade = (180.0 - self.wake_pulse_radius) / 135.0
                fade = max(0.0, min(1.0, fade))
                pulse_rgba = (56, 189, 248, int(fade * 255))
                img = draw_translucent_arc(img, (cx, cy), self.wake_pulse_radius, 0, 360, pulse_rgba, width=6)

        # Downscale via LANCZOS for high quality anti-aliasing
        resized_img = img.resize((60, 60), Image.Resampling.LANCZOS)
        self.orb_photo = ImageTk.PhotoImage(resized_img)
        self.canvas.itemconfig(self.orb_image_item, image=self.orb_photo)

        # Re-schedule at 16ms
        self.root.after(16, self.animate_orb)

    # --- Window Drag-and-Drop Handlers ---

    def _on_drag_start(self, event: tk.Event) -> None:
        self.drag_data["x"] = event.x_root
        self.drag_data["y"] = event.y_root

    def _on_drag_motion(self, event: tk.Event) -> None:
        delta_x = event.x_root - self.drag_data["x"]
        delta_y = event.y_root - self.drag_data["y"]
        if not self.root:
            return
        new_x = self.root.winfo_x() + delta_x
        new_y = self.root.winfo_y() + delta_y
        
        width = 360 if self.expanded else 280
        height = 560 if self.expanded else 60
        self.root.geometry(f"{width}x{height}+{new_x}+{new_y}")
        
        self.drag_data["x"] = event.x_root
        self.drag_data["y"] = event.y_root

    def _on_drag_release(self, event: tk.Event) -> None:
        if not self.root:
            return
        self.settings.hud_position_x = self.root.winfo_x()
        self.settings.hud_position_y = self.root.winfo_y()
        self.settings.save()

    # --- Loading History ---

    def _load_recent_history(self) -> list[dict[str, Any]]:
        from .history import HISTORY_PATH
        import json
        history = []
        if HISTORY_PATH.exists():
            try:
                with HISTORY_PATH.open("r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-15:]:
                        try:
                            record = json.loads(line)
                            if record.get("summary"):
                                history.append(record)
                        except Exception:
                            pass
            except Exception:
                pass
        return history

    # --- Thread Queue Checking ---

    def _check_queue(self) -> None:
        if not self.root:
            return
        while not self.queue.empty():
            try:
                task = self.queue.get_nowait()
                task()
            except queue.Empty:
                break
        if not self._stopped:
            self.root.after(80, self._check_queue)
