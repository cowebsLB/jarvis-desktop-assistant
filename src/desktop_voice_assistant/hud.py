from __future__ import annotations

import logging
import math
import queue
import threading
import tkinter as tk
from typing import Any
from PIL import Image, ImageDraw, ImageTk

from .config import Settings
from .models import RuntimeState, ResearchSource

LOGGER = logging.getLogger(__name__)

STATE_COLORS = {
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

        # UI state
        self.drag_data: dict[str, int] = {"x": 0, "y": 0}
        self.pulse_phase: float = 0.0
        self.wake_pulse_active: bool = False
        self.wake_pulse_radius: float = 0.0
        self.orb_items: dict[str, Any] = {}
        self.bubble_alpha: float = 0.0
        self.bubble_target_alpha: float = 0.0
        self.fade_active: bool = False
        self.yes_btn: tk.Button | None = None
        self.no_btn: tk.Button | None = None
        self.input_entry: tk.Entry | None = None

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
        self.queue.put(lambda: None)

    # --- Thread-Safe UI Update Helpers ---

    def _ui_wake_detected(self) -> None:
        self.wake_pulse_active = True
        self.wake_pulse_radius = 45.0

    def _ui_state_change(self, state: RuntimeState, reason: str | None) -> None:
        self.state = state
        self.reason = reason
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
        self.root.configure(bg="#000001")

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
        self._set_window_size(expanded=False)

        # Start loops
        self._check_queue()
        self.animate_orb()
        self._ui_set_enabled(self._enabled)

        self.root.mainloop()
        self.root = None
        self.thread = None

    def _create_widgets(self) -> None:
        if not self.root:
            return

        # Make the window background transparent by setting -transparentcolor to #000001
        self.root.configure(bg="#000001")
        self.root.wm_attributes("-transparentcolor", "#000001")

        # Main horizontal container frame (transparent)
        self.main_frame = tk.Frame(self.root, bg="#000001")
        self.main_frame.pack(fill="both", expand=True)

        # Left Side: Animated Orb Canvas (transparent bg)
        self.canvas = tk.Canvas(self.main_frame, width=60, height=60, bg="#000001", highlightthickness=0)
        self.canvas.pack(side="left", padx=5, pady=5)
        self.canvas.bind("<Button-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_release)

        # Initialize the persistent canvas image items
        self._initialize_orb_graphics()

        # Right Side: Attached Speech Bubble Frame (transparent container)
        self.bubble_frame = tk.Frame(self.main_frame, bg="#000001")

        # Canvas for speech bubble background
        self.bubble_canvas = tk.Canvas(self.bubble_frame, bg="#000001", highlightthickness=0)
        self.bubble_canvas.pack(fill="both", expand=True)
        self.bubble_canvas.bind("<Button-1>", self._on_drag_start)
        self.bubble_canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.bubble_canvas.bind("<ButtonRelease-1>", self._on_drag_release)

        # Empty background image item
        self.bg_image_item = self.bubble_canvas.create_image(0, 0, anchor="nw")

        # Inner Frame for content (with solid background color matching rounded rect fill)
        self.inner_bubble_frame = tk.Frame(self.bubble_canvas, bg="#1E293B")
        self.inner_window = self.bubble_canvas.create_window(8, 8, window=self.inner_bubble_frame, anchor="nw")

        self.bubble_lbl = tk.Label(
            self.inner_bubble_frame,
            text="",
            font=("Segoe UI", 9),
            fg="#F1F5F9",
            bg="#1E293B",
            justify="left",
            anchor="w",
            wraplength=260
        )
        self.bubble_lbl.pack(fill="both", expand=True, padx=8, pady=(4, 2))

        # Dynamic Actions sub-frame for confirmations or typing clarifications
        self.action_frame = tk.Frame(self.inner_bubble_frame, bg="#1E293B")

        # Bind configure for dynamic auto-resizing
        self.inner_bubble_frame.bind("<Configure>", self._on_bubble_configure)

    def _set_window_size(self, expanded: bool, state_val: str = "") -> None:
        if not self.root:
            return
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        if x <= 0 or y <= 0:
            x = self.settings.hud_position_x or 100
            y = self.settings.hud_position_y or 100

        if expanded:
            # Sizing is dynamically driven by _on_bubble_configure
            pass
        else:
            self.root.geometry(f"70x70+{x}+{y}")

    def _refresh_hud(self) -> None:
        if not self.root:
            return
        if not self._enabled:
            return

        state_val = self.state.value if hasattr(self.state, "value") else str(self.state)

        # Show bubble for active states
        show_bubble = state_val not in ["idle", "suspended"]

        if show_bubble:
            text = ""
            if state_val == "wake_listening":
                text = "Listening..."
            elif state_val in ["capturing_command", "transcribing"]:
                text = self.transcript or "Listening..."
            elif state_val in [
                "understanding", "planning", "researching", "fetching_sources",
                "ranking_sources", "summarizing_sources", "archiving_sources"
            ]:
                text = "Thinking..."
            elif state_val == "executing":
                text = "Executing..."
            elif state_val == "awaiting_confirmation":
                text = self.reason or "Confirmation required."
            elif state_val == "clarifying":
                text = self.reason or "Clarification required."
            elif state_val in ["speaking", "awaiting_followup"]:
                text = self.reply or self.transcript or "Speaking..."
            elif state_val == "error":
                text = self.reason or "An error occurred."
            else:
                text = "Idle"

            self.bubble_lbl.config(text=text)
            self._update_actions_ui(state_val)

            if not self.bubble_frame.winfo_manager():
                self.bubble_frame.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=5)
                if self.bubble_alpha == 0.0:
                    self.bubble_alpha = 0.0

            self.bubble_target_alpha = 1.0
            if not getattr(self, "fade_active", False):
                self._animate_bubble_fade()
        else:
            self.bubble_target_alpha = 0.0
            if not getattr(self, "fade_active", False):
                self._animate_bubble_fade()

    def _update_actions_ui(self, state_val: str) -> None:
        for w in self.action_frame.winfo_children():
            w.destroy()

        self.yes_btn = None
        self.no_btn = None
        self.input_entry = None

        if state_val == "awaiting_confirmation":
            self.action_frame.pack(fill="x", side="bottom", padx=8, pady=(0, 4))

            self.yes_btn = tk.Button(
                self.action_frame,
                text="Yes",
                font=("Segoe UI Semibold", 8, "bold"),
                fg="#F1F5F9",
                bg="#22C55E",
                activebackground="#16A34A",
                activeforeground="#F1F5F9",
                bd=0,
                padx=10,
                pady=2,
                cursor="hand2",
                command=self._confirm_yes
            )
            self.yes_btn.pack(side="left", padx=2)

            self.no_btn = tk.Button(
                self.action_frame,
                text="No",
                font=("Segoe UI Semibold", 8, "bold"),
                fg="#F1F5F9",
                bg="#EF4444",
                activebackground="#DC2626",
                activeforeground="#F1F5F9",
                bd=0,
                padx=10,
                pady=2,
                cursor="hand2",
                command=self._confirm_no
            )
            self.no_btn.pack(side="left", padx=2)

        elif state_val == "clarifying":
            self.action_frame.pack(fill="x", side="bottom", padx=8, pady=(0, 4))

            self.input_entry = tk.Entry(
                self.action_frame,
                font=("Consolas", 9),
                fg="#F1F5F9",
                bg="#0B0F19",
                insertbackground="#F1F5F9",
                bd=0,
                highlightthickness=1,
                highlightbackground="#334155",
                highlightcolor="#38BDF8"
            )
            self.input_entry.pack(fill="x", ipady=2)
            self.input_entry.bind("<Return>", self._submit_typed_text)
            self.input_entry.focus_set()
        else:
            self.action_frame.pack_forget()

    def _confirm_yes(self) -> None:
        if self.on_submit_text:
            self.on_submit_text("yes")

    def _confirm_no(self) -> None:
        if self.on_submit_text:
            self.on_submit_text("no")

    def _submit_typed_text(self, event: tk.Event) -> None:
        text = self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, tk.END)
        if self.on_submit_text:
            self.on_submit_text(text)

    # --- Speech Bubble Sizing & Fade Effects ---

    def _on_bubble_configure(self, event: tk.Event) -> None:
        if not self.root:
            return
        w = event.width
        h = event.height
        canvas_w = w + 16
        canvas_h = h + 16

        self.bubble_canvas.config(width=canvas_w, height=canvas_h)
        self._redraw_bubble_graphics()

        # Update dynamic window geometry size
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        if x <= 0 or y <= 0:
            x = self.settings.hud_position_x or 100
            y = self.settings.hud_position_y or 100

        total_w = 70 + canvas_w
        total_h = max(70, canvas_h)
        self.root.geometry(f"{total_w}x{total_h}+{x}+{y}")

    def _get_bubble_bg(self, width: int, height: int, radius: int, bg_color: str, border_color: str, alpha_mult: float) -> ImageTk.PhotoImage:
        scale = 3
        w_scaled, h_scaled = width * scale, height * scale
        r_scaled = radius * scale

        img = Image.new("RGBA", (w_scaled, h_scaled), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bg_rgba = self._hex_to_rgba(bg_color, int(220 * alpha_mult))
        border_rgba = self._hex_to_rgba(border_color, int(255 * alpha_mult))

        draw.rounded_rectangle(
            [0, 0, w_scaled - 1, h_scaled - 1],
            radius=r_scaled,
            fill=bg_rgba,
            outline=border_rgba,
            width=2 * scale
        )

        resized = img.resize((width, height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(resized)

    def _interpolate_color(self, color_start: str, color_end: str, factor: float) -> str:
        c_start = self._hex_to_rgba(color_start)
        c_end = self._hex_to_rgba(color_end)

        r = int(c_start[0] + (c_end[0] - c_start[0]) * factor)
        g = int(c_start[1] + (c_end[1] - c_start[1]) * factor)
        b = int(c_start[2] + (c_end[2] - c_start[2]) * factor)

        return f"#{r:02X}{g:02X}{b:02X}"

    def _animate_bubble_fade(self) -> None:
        if not self.root:
            self.fade_active = False
            return

        fade_speed = 0.15
        diff = self.bubble_target_alpha - self.bubble_alpha

        if abs(diff) > 0.01:
            self.fade_active = True
            if diff > 0:
                self.bubble_alpha = min(1.0, self.bubble_alpha + fade_speed)
            else:
                self.bubble_alpha = max(0.0, self.bubble_alpha - fade_speed)

            self._redraw_bubble_graphics()
            self.root.after(20, self._animate_bubble_fade)
        else:
            self.bubble_alpha = self.bubble_target_alpha
            self._redraw_bubble_graphics()
            self.fade_active = False

            if self.bubble_alpha == 0.0:
                self.bubble_frame.pack_forget()
                self._set_window_size(expanded=False)

    def _redraw_bubble_graphics(self) -> None:
        if not self.root or not self.bubble_canvas:
            return

        canvas_w = self.bubble_canvas.winfo_width()
        canvas_h = self.bubble_canvas.winfo_height()

        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w = self.bubble_canvas.winfo_reqwidth()
            canvas_h = self.bubble_canvas.winfo_reqheight()
            if canvas_w <= 1 or canvas_h <= 1:
                return

        self.bubble_photo = self._get_bubble_bg(
            canvas_w, canvas_h, radius=12, bg_color="#1E293B", border_color="#334155", alpha_mult=self.bubble_alpha
        )
        self.bubble_canvas.itemconfig(self.bg_image_item, image=self.bubble_photo)

        # Fading text colors
        text_fg = self._interpolate_color("#1E293B", "#F1F5F9", self.bubble_alpha)
        self.bubble_lbl.config(fg=text_fg)

        # Fade active interaction elements if present
        if getattr(self, "yes_btn", None) and self.yes_btn.winfo_exists():
            yes_bg = self._interpolate_color("#1E293B", "#22C55E", self.bubble_alpha)
            yes_fg = self._interpolate_color("#1E293B", "#F1F5F9", self.bubble_alpha)
            self.yes_btn.config(bg=yes_bg, fg=yes_fg)

        if getattr(self, "no_btn", None) and self.no_btn.winfo_exists():
            no_bg = self._interpolate_color("#1E293B", "#EF4444", self.bubble_alpha)
            no_fg = self._interpolate_color("#1E293B", "#F1F5F9", self.bubble_alpha)
            self.no_btn.config(bg=no_bg, fg=no_fg)

        if getattr(self, "input_entry", None) and self.input_entry.winfo_exists():
            entry_bg = self._interpolate_color("#1E293B", "#0B0F19", self.bubble_alpha)
            entry_fg = self._interpolate_color("#1E293B", "#F1F5F9", self.bubble_alpha)
            entry_border = self._interpolate_color("#1E293B", "#334155", self.bubble_alpha)
            self.input_entry.config(bg=entry_bg, fg=entry_fg, highlightbackground=entry_border)

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

        img = Image.new("RGBA", (180, 180), (0, 0, 0, 0))

        primary_rgba = self._hex_to_rgba(primary_hex, 255)
        glow_rgba = self._hex_to_rgba(glow_hex, 255)

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

        # 1. Update glow rings
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

        resized_img = img.resize((60, 60), Image.Resampling.LANCZOS)
        self.orb_photo = ImageTk.PhotoImage(resized_img)
        self.canvas.itemconfig(self.orb_image_item, image=self.orb_photo)

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

        state_val = self.state.value if hasattr(self.state, "value") else str(self.state)
        show_bubble = state_val not in ["idle", "suspended"]
        if show_bubble:
            canvas_w = self.bubble_canvas.winfo_width()
            canvas_h = self.bubble_canvas.winfo_height()
            if canvas_w <= 1:
                canvas_w = self.bubble_canvas.winfo_reqwidth()
            if canvas_h <= 1:
                canvas_h = self.bubble_canvas.winfo_reqheight()
            width = 70 + max(200, canvas_w)
            height = max(70, canvas_h)
        else:
            width, height = 70, 70

        self.root.geometry(f"{width}x{height}+{new_x}+{new_y}")

        self.drag_data["x"] = event.x_root
        self.drag_data["y"] = event.y_root

    def _on_drag_release(self, event: tk.Event) -> None:
        if not self.root:
            return
        self.settings.hud_position_x = self.root.winfo_x()
        self.settings.hud_position_y = self.root.winfo_y()
        self.settings.save()

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
