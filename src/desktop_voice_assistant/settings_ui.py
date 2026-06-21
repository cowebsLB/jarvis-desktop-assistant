from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk, messagebox

from .config import (
    Settings,
    SUPPORTED_ASSISTANT_STYLES,
    SUPPORTED_CONFIRMATION_POLICIES,
    SUPPORTED_WAKE_WORDS,
)

LOGGER = logging.getLogger(__name__)


class SettingsPanel:
    AUTO_DETECT_MIC = "Auto-detect (System Default)"

    def __init__(self, window: tk.Tk | tk.Toplevel, settings: Settings, on_save=None) -> None:
        self.window = window
        self.settings = settings
        self.on_save = on_save

        self.window.title("Jarvis Config")
        self.window.configure(bg="#0F172A")
        self.window.geometry("480x880")
        self.window.resizable(False, False)

        # Apply premium styling to ttk elements
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure frame and label styles
        style.configure("TFrame", background="#0F172A")
        style.configure("TLabel", background="#0F172A", foreground="#F1F5F9", font=("Segoe UI", 9))
        
        # Configure custom modern Combobox styling
        style.configure("TCombobox", 
                        fieldbackground="#0F172A", 
                        background="#334155", 
                        foreground="#F1F5F9", 
                        bordercolor="#334155", 
                        lightcolor="#334155", 
                        darkcolor="#334155",
                        arrowcolor="#38BDF8")
        style.map("TCombobox", 
                  fieldbackground=[("readonly", "#0F172A"), ("active", "#1E293B")],
                  foreground=[("readonly", "#F1F5F9"), ("active", "#F1F5F9")],
                  selectbackground=[("readonly", "#0F172A")],
                  selectforeground=[("readonly", "#F1F5F9")])

        # Apply dark theme styling to dropdown listboxes globally
        self.window.option_add("*TCombobox*Listbox.background", "#0F172A")
        self.window.option_add("*TCombobox*Listbox.foreground", "#F1F5F9")
        self.window.option_add("*TCombobox*Listbox.selectBackground", "#38BDF8")
        self.window.option_add("*TCombobox*Listbox.selectForeground", "#0F172A")
        self.window.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))
        self.window.option_add("*TCombobox*Listbox.relief", "flat")
        self.window.option_add("*TCombobox*Listbox.borderWidth", "0")

        # Main outer container
        outer_container = tk.Frame(self.window, bg="#0F172A")
        outer_container.pack(fill="both", expand=True)

        # Smooth, customized canvas scrollable area
        self.canvas = tk.Canvas(
            outer_container,
            bg="#0F172A",
            highlightthickness=0,
            bd=0,
        )
        self.scrollbar = tk.Scrollbar(
            outer_container,
            orient="vertical",
            command=self.canvas.yview,
            bg="#1E293B",
            activebackground="#334155",
            troughcolor="#0F172A",
            bd=0,
            width=10,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Content frame inside the canvas
        self.main_container = tk.Frame(self.canvas, bg="#0F172A", padx=16, pady=20)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.main_container, anchor="nw")
        
        self.main_container.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Header Title Frame
        title_frame = tk.Frame(self.main_container, bg="#0F172A")
        title_frame.pack(fill="x", pady=(0, 10))
        
        title_lbl = tk.Label(
            title_frame,
            text="JARVIS CONTROL PANEL",
            font=("Segoe UI Semibold", 14, "bold"),
            fg="#38BDF8",
            bg="#0F172A"
        )
        title_lbl.pack(anchor="w")
        
        subtitle_lbl = tk.Label(
            title_frame,
            text="System preferences & parameters",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#0F172A"
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # 1. Card: General Settings
        card_gen = self._create_section_card("General Settings")
        self.assistant_name_var = tk.StringVar(value=self.settings.assistant_name)
        self._create_field_entry(card_gen, "Assistant Name", self.assistant_name_var)
        self.assistant_style_var = tk.StringVar(value=self.settings.assistant_style)
        self._create_field_combo(card_gen, "Assistant Style", self.assistant_style_var, sorted(SUPPORTED_ASSISTANT_STYLES))
        self.default_location_var = tk.StringVar(value=self.settings.default_location)
        self._create_field_entry(card_gen, "Default Location", self.default_location_var)

        # 2. Card: Voice & Wake Word
        card_voice = self._create_section_card("Voice & Wake Word")
        self.wake_enabled_var = tk.BooleanVar(value=self.settings.wake_word_enabled)
        self._create_field_check(card_voice, "Enable Wake Word Detection", self.wake_enabled_var)
        self.wake_cue_var = tk.BooleanVar(value=self.settings.wake_cue_enabled)
        self._create_field_check(card_voice, "Play Audible Listening Cue", self.wake_cue_var)
        self.wake_phrase_var = tk.StringVar(value=self.settings.wake_word_phrase)
        self._create_field_combo(card_voice, "Wake Phrase", self.wake_phrase_var, sorted(list(SUPPORTED_WAKE_WORDS)))
        
        # Microphones
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            mic_devices = [self.AUTO_DETECT_MIC]
            for d in devices:
                if d.get("max_input_channels", 0) > 0:
                    name = d.get("name")
                    if name and name not in mic_devices:
                        mic_devices.append(name)
        except Exception:
            mic_devices = [self.AUTO_DETECT_MIC]

        self.mic_devices = mic_devices
        initial_mic = self._resolve_initial_microphone_choice(self.settings.microphone_device, mic_devices)
        self.mic_device_var = tk.StringVar(value=initial_mic)
        self._create_field_combo(card_voice, "Input Microphone", self.mic_device_var, mic_devices)
        
        self.speech_rate_var = tk.IntVar(value=self.settings.speech_rate)
        self._create_field_slider(card_voice, "Speech Rate (WPM)", self.speech_rate_var, 100, 300)

        # 3. Card: Intelligence & Search
        card_ai = self._create_section_card("Intelligence & Search")
        self.semantic_retrieval_var = tk.BooleanVar(value=self.settings.semantic_retrieval_enabled)
        self._create_field_check(card_ai, "Enable Semantic Local Retrieval", self.semantic_retrieval_var)
        self.archive_enabled_var = tk.BooleanVar(value=self.settings.web_archive_enabled)
        self._create_field_check(card_ai, "Archive Web Research History", self.archive_enabled_var)
        self.open_after_answer_var = tk.BooleanVar(value=self.settings.web_open_after_answer)
        self._create_field_check(card_ai, "Auto-Open Top Web Research Source", self.open_after_answer_var)
        
        self.ollama_model_var = tk.StringVar(value=self.settings.ollama_model)
        self._create_field_entry(card_ai, "Ollama LLM Model", self.ollama_model_var)
        self.gemini_enabled_var = tk.BooleanVar(value=self.settings.gemini_enabled)
        self._create_field_check(card_ai, "Gemini Complexity Fallback", self.gemini_enabled_var)
        self.gemini_model_var = tk.StringVar(value=self.settings.gemini_model)
        self._create_field_entry(card_ai, "Gemini LLM Model", self.gemini_model_var)
        self.embedding_model_var = tk.StringVar(value=self.settings.embedding_model)
        self._create_field_entry(card_ai, "Local Embedding Model", self.embedding_model_var)
        
        self.fetch_limit_var = tk.IntVar(value=self.settings.web_fetch_limit)
        self._create_field_slider(card_ai, "Search Fetch Limit", self.fetch_limit_var, 1, 10)
        self.archive_recall_var = tk.IntVar(value=self.settings.archive_recall_limit)
        self._create_field_slider(card_ai, "Archive Recall Limit", self.archive_recall_var, 1, 10)

        # 4. Card: HUD & System
        card_hud = self._create_section_card("HUD & System Policies")
        self.hud_enabled_var = tk.BooleanVar(value=self.settings.hud_enabled)
        self._create_field_check(card_hud, "Enable Floating HUD Overlay", self.hud_enabled_var)
        self.confirmation_policy_var = tk.StringVar(value=self.settings.confirmation_policy)
        self._create_field_combo(card_hud, "Confirmation Policy", self.confirmation_policy_var, sorted(SUPPORTED_CONFIRMATION_POLICIES))
        self.followup_var = tk.IntVar(value=self.settings.conversation_followup_seconds)
        self._create_field_slider(card_hud, "Follow-up Timeout (s)", self.followup_var, 10, 120)

        # Button Panel
        btn_frame = tk.Frame(self.main_container, bg="#0F172A")
        btn_frame.pack(fill="x", side="bottom", pady=(20, 0))

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI Semibold", 9),
            fg="#F1F5F9",
            bg="#334155",
            activebackground="#475569",
            activeforeground="#F1F5F9",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._cancel
        )
        cancel_btn.pack(side="right", padx=5)

        save_btn = tk.Button(
            btn_frame,
            text="Save Configuration",
            font=("Segoe UI Semibold", 9, "bold"),
            fg="#F1F5F9",
            bg="#10B981",
            activebackground="#059669",
            activeforeground="#F1F5F9",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._save_settings
        )
        save_btn.pack(side="right", padx=5)

        # Hover effects for modern look
        def on_enter_save(e):
            save_btn.config(bg="#34D399")
        def on_leave_save(e):
            save_btn.config(bg="#10B981")
        save_btn.bind("<Enter>", on_enter_save)
        save_btn.bind("<Leave>", on_leave_save)

        def on_enter_cancel(e):
            cancel_btn.config(bg="#475569")
        def on_leave_cancel(e):
            cancel_btn.config(bg="#334155")
        cancel_btn.bind("<Enter>", on_enter_cancel)
        cancel_btn.bind("<Leave>", on_leave_cancel)

    def _on_content_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        if not self.window.winfo_exists():
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    @classmethod
    def _resolve_initial_microphone_choice(cls, configured_device: str | None, available_devices: list[str]) -> str:
        if not configured_device:
            return cls.AUTO_DETECT_MIC
        if configured_device in available_devices:
            return configured_device
        return cls.AUTO_DETECT_MIC

    def _create_section_card(self, title: str) -> tk.Frame:
        card = tk.Frame(self.main_container, bg="#1E293B", highlightthickness=1, highlightbackground="#334155")
        card.pack(fill="x", pady=8, ipady=4)

        header_frame = tk.Frame(card, bg="#1E293B")
        header_frame.pack(fill="x", padx=12, pady=(8, 4))
        
        lbl = tk.Label(header_frame, text=title.upper(), font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#1E293B")
        lbl.pack(side="left")
        
        divider = tk.Frame(header_frame, height=1, bg="#334155")
        divider.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)
        
        return card

    def _create_field_entry(self, card: tk.Frame, label_text: str, var: tk.StringVar) -> None:
        grid_frame = tk.Frame(card, bg="#1E293B")
        grid_frame.pack(fill="x", padx=12, pady=4)
        
        lbl = tk.Label(grid_frame, text=label_text, font=("Segoe UI", 9), fg="#94A3B8", bg="#1E293B", anchor="w", width=18)
        lbl.pack(side="left")
        
        entry = tk.Entry(
            grid_frame,
            textvariable=var,
            font=("Segoe UI", 9),
            fg="#F1F5F9",
            bg="#0F172A",
            insertbackground="#F1F5F9",
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground="#334155",
            highlightcolor="#38BDF8",
        )
        entry.pack(side="left", fill="x", expand=True, padx=(5, 0), ipady=3)

    def _create_field_combo(self, card: tk.Frame, label_text: str, var: tk.StringVar, values: list[str]) -> ttk.Combobox:
        grid_frame = tk.Frame(card, bg="#1E293B")
        grid_frame.pack(fill="x", padx=12, pady=4)
        
        lbl = tk.Label(grid_frame, text=label_text, font=("Segoe UI", 9), fg="#94A3B8", bg="#1E293B", anchor="w", width=18)
        lbl.pack(side="left")
        
        combo = ttk.Combobox(
            grid_frame,
            textvariable=var,
            values=values,
            state="readonly",
        )
        combo.pack(side="left", fill="x", expand=True, padx=(5, 0))
        return combo

    def _create_field_check(self, card: tk.Frame, label_text: str, var: tk.BooleanVar) -> None:
        grid_frame = tk.Frame(card, bg="#1E293B")
        grid_frame.pack(fill="x", padx=12, pady=4)
        
        chk = tk.Checkbutton(
            grid_frame,
            text=label_text,
            variable=var,
            font=("Segoe UI", 9),
            fg="#F1F5F9",
            bg="#1E293B",
            activebackground="#1E293B",
            activeforeground="#F1F5F9",
            selectcolor="#0F172A",
            highlightthickness=0,
            bd=0
        )
        chk.pack(side="left", fill="both", expand=True)

    def _create_field_slider(self, card: tk.Frame, label_text: str, var: tk.Variable, from_: int, to_: int) -> tk.Scale:
        grid_frame = tk.Frame(card, bg="#1E293B")
        grid_frame.pack(fill="x", padx=12, pady=4)
        
        lbl = tk.Label(grid_frame, text=label_text, font=("Segoe UI", 9), fg="#94A3B8", bg="#1E293B", anchor="w", width=18)
        lbl.pack(side="left")
        
        scale = tk.Scale(
            grid_frame,
            from_=from_,
            to_=to_,
            orient="horizontal",
            variable=var,
            bg="#1E293B",
            fg="#F1F5F9",
            highlightthickness=0,
            troughcolor="#0F172A",
            activebackground="#38BDF8",
            bd=0,
            showvalue=True,
        )
        scale.pack(side="left", fill="x", expand=True, padx=(5, 0))
        return scale

    def _save_settings(self) -> None:
        # Validate values
        assistant_name = self.assistant_name_var.get().strip()
        if not assistant_name:
            messagebox.showerror("Validation Error", "Assistant Name cannot be empty.", parent=self.window)
            return

        default_location = self.default_location_var.get().strip()
        if not default_location:
            messagebox.showerror("Validation Error", "Default Location cannot be empty.", parent=self.window)
            return

        ollama_model = self.ollama_model_var.get().strip()
        if not ollama_model:
            messagebox.showerror("Validation Error", "Ollama LLM Model name cannot be empty.", parent=self.window)
            return

        embedding_model = self.embedding_model_var.get().strip()
        if not embedding_model:
            messagebox.showerror("Validation Error", "Embedding model name cannot be empty.", parent=self.window)
            return

        # Write updates back to settings object
        self.settings.assistant_name = assistant_name
        self.settings.assistant_style = self.assistant_style_var.get()
        self.settings.confirmation_policy = self.confirmation_policy_var.get()
        self.settings.default_location = default_location
        self.settings.wake_word_enabled = self.wake_enabled_var.get()
        self.settings.wake_cue_enabled = self.wake_cue_var.get()
        self.settings.wake_word_phrase = self.wake_phrase_var.get()
        self.settings.speech_rate = self.speech_rate_var.get()
        mic_val = self.mic_device_var.get()
        self.settings.microphone_device = None if mic_val == self.AUTO_DETECT_MIC else mic_val
        self.settings.semantic_retrieval_enabled = self.semantic_retrieval_var.get()
        self.settings.web_archive_enabled = self.archive_enabled_var.get()
        self.settings.web_open_after_answer = self.open_after_answer_var.get()
        self.settings.ollama_model = ollama_model
        self.settings.gemini_enabled = self.gemini_enabled_var.get()
        self.settings.gemini_model = self.gemini_model_var.get().strip() or self.settings.gemini_model
        self.settings.embedding_model = embedding_model
        self.settings.web_fetch_limit = self.fetch_limit_var.get()
        self.settings.archive_recall_limit = self.archive_recall_var.get()
        self.settings.hud_enabled = self.hud_enabled_var.get()
        self.settings.conversation_followup_seconds = self.followup_var.get()

        # Save to disk
        try:
            self.settings.save()
            LOGGER.info("Settings saved successfully via UI panel")
            if self.on_save:
                self.on_save()
            self.window.destroy()
        except Exception as exc:
            messagebox.showerror("Save Failure", f"Failed to save settings: {exc}", parent=self.window)

    def _cancel(self) -> None:
        self.window.destroy()
