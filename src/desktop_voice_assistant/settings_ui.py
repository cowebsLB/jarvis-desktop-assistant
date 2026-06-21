from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk, messagebox

from .config import Settings, SUPPORTED_WAKE_WORDS

LOGGER = logging.getLogger(__name__)


class SettingsPanel:
    def __init__(self, window: tk.Tk | tk.Toplevel, settings: Settings, on_save=None) -> None:
        self.window = window
        self.settings = settings
        self.on_save = on_save

        self.window.title("Jarvis Settings")
        self.window.configure(bg="#0F172A")
        self.window.geometry("450x670")
        self.window.resizable(False, False)

        # Apply basic styling to ttk elements
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#0F172A")
        style.configure("TLabel", background="#0F172A", foreground="#F1F5F9", font=("Segoe UI", 9))
        style.configure("TCheckbutton", background="#0F172A", foreground="#F1F5F9", font=("Segoe UI", 9))

        # Main scrollable canvas (if needed, but 450x640 fits everything perfectly with Grid)
        self.main_container = tk.Frame(self.window, bg="#0F172A", padx=20, pady=15)
        self.main_container.pack(fill="both", expand=True)

        # Title
        title_lbl = tk.Label(
            self.main_container,
            text="JARVIS SYSTEM CONFIGURATION",
            font=("Segoe UI", 12, "bold"),
            fg="#38BDF8",
            bg="#0F172A"
        )
        title_lbl.pack(fill="x", pady=(0, 15))

        # 1. Section: General
        self._create_section_header("General Settings")
        gen_frame = tk.Frame(self.main_container, bg="#0F172A")
        gen_frame.pack(fill="x", pady=5)
        
        self.assistant_name_var = tk.StringVar(value=self.settings.assistant_name)
        self._create_field_entry(gen_frame, "Assistant Name:", self.assistant_name_var, 0)

        self.default_location_var = tk.StringVar(value=self.settings.default_location)
        self._create_field_entry(gen_frame, "Default Location:", self.default_location_var, 1)

        # 2. Section: Speech & Listening
        self._create_section_header("Voice & Wake Word")
        speech_frame = tk.Frame(self.main_container, bg="#0F172A")
        speech_frame.pack(fill="x", pady=5)

        self.wake_enabled_var = tk.BooleanVar(value=self.settings.wake_word_enabled)
        self._create_field_check(speech_frame, "Wake Word Enabled", self.wake_enabled_var, 0)

        # Wake word phrase dropdown
        lbl = tk.Label(speech_frame, text="Wake Phrase:", font=("Segoe UI", 9), fg="#94A3B8", bg="#0F172A", anchor="w")
        lbl.grid(row=1, column=0, sticky="w", pady=4)
        
        self.wake_phrase_var = tk.StringVar(value=self.settings.wake_word_phrase)
        wake_words = sorted(list(SUPPORTED_WAKE_WORDS))
        self.wake_phrase_menu = ttk.Combobox(
            speech_frame, 
            textvariable=self.wake_phrase_var, 
            values=wake_words, 
            state="readonly",
            width=22
        )
        self.wake_phrase_menu.grid(row=1, column=1, sticky="w", pady=4, padx=5)

        # Microphone input device dropdown
        lbl_mic = tk.Label(speech_frame, text="Microphone:", font=("Segoe UI", 9), fg="#94A3B8", bg="#0F172A", anchor="w")
        lbl_mic.grid(row=2, column=0, sticky="w", pady=4)
        
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            mic_devices = ["Default"]
            for d in devices:
                if d.get("max_input_channels", 0) > 0:
                    name = d.get("name")
                    if name and name not in mic_devices:
                        mic_devices.append(name)
        except Exception:
            mic_devices = ["Default"]
            
        initial_mic = self.settings.microphone_device or "Default"
        self.mic_device_var = tk.StringVar(value=initial_mic)
        self.mic_menu = ttk.Combobox(
            speech_frame,
            textvariable=self.mic_device_var,
            values=mic_devices,
            state="readonly",
            width=22
        )
        self.mic_menu.grid(row=2, column=1, sticky="w", pady=4, padx=5)

        # Speech rate slider
        lbl_rate = tk.Label(speech_frame, text="Speech Rate (WPM):", font=("Segoe UI", 9), fg="#94A3B8", bg="#0F172A", anchor="w")
        lbl_rate.grid(row=3, column=0, sticky="w", pady=4)
        
        self.speech_rate_var = tk.IntVar(value=self.settings.speech_rate)
        self.rate_scale = tk.Scale(
            speech_frame,
            from_=100,
            to_=300,
            orient="horizontal",
            variable=self.speech_rate_var,
            bg="#0F172A",
            fg="#F1F5F9",
            highlightthickness=0,
            troughcolor="#1E293B",
            activebackground="#38BDF8"
        )
        self.rate_scale.grid(row=3, column=1, sticky="we", pady=4, padx=5)

        # 3. Section: Local AI & Web Search
        self._create_section_header("Intelligence & Search")
        ai_frame = tk.Frame(self.main_container, bg="#0F172A")
        ai_frame.pack(fill="x", pady=5)

        self.semantic_retrieval_var = tk.BooleanVar(value=self.settings.semantic_retrieval_enabled)
        self._create_field_check(ai_frame, "Enable Semantic Retrieval", self.semantic_retrieval_var, 0)

        self.ollama_model_var = tk.StringVar(value=self.settings.ollama_model)
        self._create_field_entry(ai_frame, "Ollama LLM Model:", self.ollama_model_var, 1)

        self.embedding_model_var = tk.StringVar(value=self.settings.embedding_model)
        self._create_field_entry(ai_frame, "Embedding Model:", self.embedding_model_var, 2)

        # Web fetch limit slider
        lbl_limit = tk.Label(ai_frame, text="Search Fetch Limit:", font=("Segoe UI", 9), fg="#94A3B8", bg="#0F172A", anchor="w")
        lbl_limit.grid(row=3, column=0, sticky="w", pady=4)
        
        self.fetch_limit_var = tk.IntVar(value=self.settings.web_fetch_limit)
        self.limit_scale = tk.Scale(
            ai_frame,
            from_=1,
            to_=10,
            orient="horizontal",
            variable=self.fetch_limit_var,
            bg="#0F172A",
            fg="#F1F5F9",
            highlightthickness=0,
            troughcolor="#1E293B",
            activebackground="#38BDF8"
        )
        self.limit_scale.grid(row=3, column=1, sticky="we", pady=4, padx=5)

        # 4. Section: Interface & HUD
        self._create_section_header("HUD & System")
        hud_frame = tk.Frame(self.main_container, bg="#0F172A")
        hud_frame.pack(fill="x", pady=5)

        self.hud_enabled_var = tk.BooleanVar(value=self.settings.hud_enabled)
        self._create_field_check(hud_frame, "Enable Floating HUD Overlay", self.hud_enabled_var, 0)

        # Follow-up timeout slider
        lbl_timeout = tk.Label(hud_frame, text="Follow-up Timeout (s):", font=("Segoe UI", 9), fg="#94A3B8", bg="#0F172A", anchor="w")
        lbl_timeout.grid(row=1, column=0, sticky="w", pady=4)
        
        self.followup_var = tk.IntVar(value=self.settings.conversation_followup_seconds)
        self.timeout_scale = tk.Scale(
            hud_frame,
            from_=10,
            to_=120,
            orient="horizontal",
            variable=self.followup_var,
            bg="#0F172A",
            fg="#F1F5F9",
            highlightthickness=0,
            troughcolor="#1E293B",
            activebackground="#38BDF8"
        )
        self.timeout_scale.grid(row=1, column=1, sticky="we", pady=4, padx=5)

        # Buttons
        btn_frame = tk.Frame(self.main_container, bg="#0F172A")
        btn_frame.pack(fill="x", side="bottom", pady=(15, 0))

        # Save Button
        save_btn = tk.Button(
            btn_frame,
            text="Save Configuration",
            font=("Segoe UI", 9, "bold"),
            fg="#F1F5F9",
            bg="#10B981",
            activebackground="#059669",
            activeforeground="#F1F5F9",
            bd=0,
            padx=15,
            pady=6,
            command=self._save_settings
        )
        save_btn.pack(side="right", padx=5)

        # Cancel Button
        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 9),
            fg="#F1F5F9",
            bg="#475569",
            activebackground="#334155",
            activeforeground="#F1F5F9",
            bd=0,
            padx=15,
            pady=6,
            command=self._cancel
        )
        cancel_btn.pack(side="right", padx=5)

    def _create_section_header(self, title: str) -> None:
        header_frame = tk.Frame(self.main_container, bg="#0F172A")
        header_frame.pack(fill="x", pady=(10, 2))
        
        lbl = tk.Label(header_frame, text=title.upper(), font=("Segoe UI", 8, "bold"), fg="#38BDF8", bg="#0F172A")
        lbl.pack(side="left")
        
        divider = tk.Frame(header_frame, height=1, bg="#1E293B")
        divider.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)

    def _create_field_entry(self, parent: tk.Frame, label_text: str, var: tk.StringVar, row: int) -> None:
        lbl = tk.Label(parent, text=label_text, font=("Segoe UI", 9), fg="#94A3B8", bg="#0F172A", anchor="w")
        lbl.grid(row=row, column=0, sticky="w", pady=4)
        
        entry = tk.Entry(
            parent,
            textvariable=var,
            font=("Segoe UI", 9),
            fg="#F1F5F9",
            bg="#1E293B",
            insertbackground="#F1F5F9",
            bd=1,
            relief="solid",
            width=25
        )
        entry.grid(row=row, column=1, sticky="w", pady=4, padx=5)

    def _create_field_check(self, parent: tk.Frame, label_text: str, var: tk.BooleanVar, row: int) -> None:
        chk = tk.Checkbutton(
            parent,
            text=label_text,
            variable=var,
            font=("Segoe UI", 9),
            fg="#F1F5F9",
            bg="#0F172A",
            activebackground="#0F172A",
            activeforeground="#F1F5F9",
            selectcolor="#1E293B",
            highlightthickness=0,
            bd=0
        )
        chk.grid(row=row, column=0, columnspan=2, sticky="w", pady=4)

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
        self.settings.default_location = default_location
        self.settings.wake_word_enabled = self.wake_enabled_var.get()
        self.settings.wake_word_phrase = self.wake_phrase_var.get()
        self.settings.speech_rate = self.speech_rate_var.get()
        mic_val = self.mic_device_var.get()
        self.settings.microphone_device = None if mic_val == "Default" else mic_val
        self.settings.semantic_retrieval_enabled = self.semantic_retrieval_var.get()
        self.settings.ollama_model = ollama_model
        self.settings.embedding_model = embedding_model
        self.settings.web_fetch_limit = self.fetch_limit_var.get()
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
