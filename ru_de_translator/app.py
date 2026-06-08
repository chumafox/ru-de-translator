"""RU-DE Translator TUI — main application.

A Textual-based terminal interface for translating Russian to German
with neural TTS pronunciation.

Keyboard shortcuts:
    Enter   — Translate
    F1      — Settings
    Ctrl+P  — Pronounce
    Ctrl+S  — Stop Audio
    Ctrl+Q  — Quit
"""

import asyncio
import logging
import sys
import os

# Disable tqdm and its monitor thread to prevent Python 3.13 fatal errors during shutdown
# and to prevent progress bars from corrupting the Textual TUI.
os.environ["TQDM_DISABLE"] = "1"

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Input, Label, Button, Select, Checkbox, Static
from textual.binding import Binding

from ru_de_translator.config import load_config, save_config, setup_logging
from ru_de_translator.translator import Translator, TranslationError
from ru_de_translator.tts import TTSEngine, TTSError

logger = logging.getLogger(__name__)


# ── Global exception handler ───────────────────────────────────────────

def _setup_excepthook() -> None:
    """Logs uncaught exceptions instead of printing to stderr (which is hidden in TUI)."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


# ── Settings Screen ────────────────────────────────────────────────────

class SettingsScreen(ModalScreen[dict]):
    """Modal dialog for configuring translation and TTS settings."""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config.copy()
        self._voice_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        providers = [
            ("Gemini API", "gemini"),
            ("Ollama (Local LLM)", "ollama"),
            ("LM Studio (Local LLM)", "lm_studio"),
            ("translateLocally (Local MT)", "translatelocally"),
            ("CTranslate2 (Local MT)", "ctranslate2"),
        ]

        with Container(id="settings-dialog"):
            yield Label("⚙ SETTINGS", id="settings-title")

            with VerticalScroll(id="settings-scroll-container"):
                yield Label("Translation Provider:", classes="settings-label")
                yield Select(
                    providers,
                    value=self.config.get("translation_provider", "ctranslate2"),
                    id="select-provider",
                    classes="settings-select",
                )

                yield Label("Gemini API Key:", classes="settings-label")
                yield Input(
                    value=self.config.get("gemini_api_key", ""),
                    password=True,
                    placeholder="Gemini API Key...",
                    id="input-gemini-key",
                )

                yield Label("Gemini Model:", classes="settings-label")
                yield Input(
                    value=self.config.get("gemini_model", ""),
                    placeholder="e.g. gemini-2.5-flash",
                    id="input-gemini-model",
                )

                yield Label("Ollama URL:", classes="settings-label")
                yield Input(
                    value=self.config.get("ollama_url", ""),
                    placeholder="e.g. http://localhost:11434",
                    id="input-ollama-url",
                )

                yield Label("Ollama Model:", classes="settings-label")
                yield Input(
                    value=self.config.get("ollama_model", ""),
                    placeholder="e.g. qwen2.5:7b",
                    id="input-ollama-model",
                )

                yield Label("LM Studio URL:", classes="settings-label")
                yield Input(
                    value=self.config.get("lm_studio_url", ""),
                    placeholder="e.g. http://localhost:1234/v1",
                    id="input-lm-studio-url",
                )

                yield Label("LM Studio Model:", classes="settings-label")
                yield Input(
                    value=self.config.get("lm_studio_model", ""),
                    placeholder="e.g. local-model",
                    id="input-lm-studio-model",
                )

                yield Label("translateLocally Path:", classes="settings-label")
                yield Input(
                    value=self.config.get("translatelocally_bin", ""),
                    placeholder="e.g. /Applications/translateLocally.app/Contents/MacOS/translateLocally",
                    id="input-translatelocally-bin",
                )

                yield Label("translateLocally Model:", classes="settings-label")
                yield Input(
                    value=self.config.get("translatelocally_model", ""),
                    placeholder="e.g. ru-de",
                    id="input-translatelocally-model",
                )

                yield Label("CTranslate2 Model Path:", classes="settings-label")
                yield Input(
                    value=self.config.get("ctranslate2_model_path", ""),
                    placeholder="e.g. ~/.config/ru_de_translator/opus-zle-de-ct2",
                    id="input-ctranslate2-path",
                )

                yield Label("CTranslate2 Tokenizer Name:", classes="settings-label")
                yield Input(
                    value=self.config.get("ctranslate2_tokenizer_name", ""),
                    placeholder="e.g. Helsinki-NLP/opus-mt-tc-big-zle-de",
                    id="input-ctranslate2-tokenizer",
                )

                yield Label("TTS Engine:", classes="settings-label")
                tts_providers = [
                    ("Qwen3-TTS (Local, Neural)", "qwen_tts"),
                    ("Microsoft Edge TTS (Online)", "edge_tts")
                ]
                yield Select(
                    tts_providers, 
                    value=self.config.get("tts_provider", "qwen_tts"), 
                    id="select-tts-provider", 
                    classes="settings-select"
                )

                yield Label("Qwen TTS Model:", classes="settings-label")
                yield Input(
                    value=self.config.get("qwen_tts_model", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"),
                    placeholder="e.g. Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                    id="input-qwen-tts-model",
                )
                
                yield Label("Qwen TTS Voice:", classes="settings-label")
                saved_voice = self.config.get("qwen_tts_voice", "ryan")
                qwen_voices = [
                    ("Aiden (Male)", "aiden"),
                    ("Dylan (Male)", "dylan"),
                    ("Eric (Male)", "eric"),
                    ("Ono Anna (Female)", "ono_anna"),
                    ("Ryan (Male)", "ryan"),
                    ("Serena (Female)", "serena"),
                    ("Sohee (Female)", "sohee"),
                    ("Uncle Fu (Male)", "uncle_fu"),
                    ("Vivian (Female)", "vivian")
                ]
                if saved_voice not in [v[1] for v in qwen_voices]:
                    saved_voice = "ryan"
                yield Select(
                    qwen_voices,
                    value=saved_voice,
                    id="select-qwen-tts-voice",
                    classes="settings-select",
                )

                yield Label("Edge TTS German Voice:", classes="settings-label")
                yield Select([], id="select-voice", classes="settings-select")

                yield Checkbox(
                    "Auto Pronounce on Translate",
                    value=self.config.get("auto_pronounce", True),
                    id="check-auto-pronounce",
                )

                yield Label("Practice Repeats:", classes="settings-label")
                yield Input(
                    value=str(self.config.get("practice_repeats", 3)),
                    placeholder="e.g. 3",
                    id="input-practice-repeats",
                )

                yield Label("Practice Pause (sec):", classes="settings-label")
                yield Input(
                    value=str(self.config.get("practice_pause", 2.0)),
                    placeholder="e.g. 2.0",
                    id="input-practice-pause",
                )

            with Container(id="settings-buttons"):
                yield Button("Save", id="btn-save-settings")
                yield Button("Cancel", id="btn-cancel-settings")

    def on_mount(self) -> None:
        """Populate voice dropdown asynchronously on mount."""
        self._voice_task = asyncio.create_task(self._load_voices())

    async def _load_voices(self) -> None:
        """Loads available Edge TTS voices into the Select widget."""
        voice_select = self.query_one("#select-voice", Select)
        voice_select.set_options([("Loading voices...", "loading")])
        voice_select.value = "loading"

        try:
            voices = await TTSEngine.get_edge_voices()
            options = [(v["friendly_name"], v["name"]) for v in voices]
            voice_select.set_options(options)

            default_voice = self.config.get("edge_voice", "de-DE-KatjaNeural")
            available_values = {val for _, val in options}
            if default_voice in available_values:
                voice_select.value = default_voice
            elif options:
                voice_select.value = options[0][1]
        except Exception:
            logger.warning("Failed to load voices", exc_info=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-settings":
            self._save_and_dismiss()
        elif event.button.id == "btn-cancel-settings":
            self.dismiss(None)

    def _save_and_dismiss(self) -> None:
        """Collect all input values, update config, and dismiss."""
        # Read Select values safely (may be Select.BLANK)
        provider_val = self.query_one("#select-provider", Select).value
        voice_val = self.query_one("#select-voice", Select).value

        tts_val = self.query_one("#select-tts-provider", Select).value

        if provider_val is not Select.BLANK:
            self.config["translation_provider"] = provider_val
            
        if tts_val is not Select.BLANK:
            self.config["tts_provider"] = tts_val

        if voice_val not in (Select.BLANK, "loading"):
            self.config["edge_voice"] = voice_val

        # Read text inputs
        self.config.update({
            "gemini_api_key": self.query_one("#input-gemini-key", Input).value,
            "gemini_model": self.query_one("#input-gemini-model", Input).value,
            "ollama_url": self.query_one("#input-ollama-url", Input).value,
            "ollama_model": self.query_one("#input-ollama-model", Input).value,
            "lm_studio_url": self.query_one("#input-lm-studio-url", Input).value,
            "lm_studio_model": self.query_one("#input-lm-studio-model", Input).value,
            "translatelocally_bin": self.query_one("#input-translatelocally-bin", Input).value,
            "translatelocally_model": self.query_one("#input-translatelocally-model", Input).value,
            "ctranslate2_model_path": self.query_one("#input-ctranslate2-path", Input).value,
            "ctranslate2_tokenizer_name": self.query_one("#input-ctranslate2-tokenizer", Input).value,
            "qwen_tts_model": self.query_one("#input-qwen-tts-model", Input).value,
            "qwen_tts_voice": self.query_one("#select-qwen-tts-voice", Select).value,
            "auto_pronounce": self.query_one("#check-auto-pronounce", Checkbox).value,
            "practice_repeats": int(self.query_one("#input-practice-repeats", Input).value or 3),
            "practice_pause": float(self.query_one("#input-practice-pause", Input).value or 2.0),
        })

        self.dismiss(self.config)


# ── Main Application ───────────────────────────────────────────────────

class TranslatorApp(App):
    """A Textual TUI for Russian-German translation with Text-to-Speech."""

    TITLE = "RU-DE Translator (Beta)"
    CSS_PATH = "style.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("f1", "open_settings", "Settings", show=True),
        Binding("ctrl+p", "speak", "Pronounce", show=True),
        Binding("alt+r", "practice", "Practice", show=True),
        Binding("ctrl+e", "export_practice", "Export", show=True),
        Binding("ctrl+s", "stop", "Stop Audio", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.translator = Translator(self.config)
        self.tts = TTSEngine(self.config)
        self._last_translation: str = ""
        self.session_history: list[tuple[list[bytes], str]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield Label("Enter Russian Text:", classes="section-title")
            yield Input(
                placeholder="Type Russian word or phrase and press Enter...",
                id="input-text",
            )

            yield Label("German Translation:", classes="section-title")
            with Container(id="result-container"):
                yield Static("", id="result-text")

            yield Label("Status:", classes="section-title")
            yield Static("Ready", id="status-msg")

            with Container(id="buttons-layout"):
                yield Button("Translate (Enter)", id="btn-translate")
                yield Button("Pronounce (Ctrl+P)", id="btn-speak")
                yield Button("Practice (Alt+R)", id="btn-practice")
                yield Button("Export Audio (Ctrl+E)", id="btn-export", variant="warning")
                yield Button("Stop Audio (Ctrl+S)", id="btn-stop")
                yield Button("Settings (F1)", id="btn-settings")
        yield Footer()

    def on_mount(self) -> None:
        logger.info("RU-DE Translator TUI started successfully.")
        self._update_title_bar()
        self.query_one("#input-text", Input).focus()
        # Warmup models in background to avoid latency
        asyncio.create_task(self.tts.warmup())
        # Setup idle timer for unloading models
        self._idle_timer = self.set_timer(300, self._unload_models)

    def _reset_idle_timer(self) -> None:
        """Resets the auto-unload idle timer."""
        if hasattr(self, "_idle_timer"):
            self._idle_timer.reset()

    def _unload_models(self) -> None:
        """Unloads models to free RAM after inactivity."""
        logger.info("Idle timeout reached. Unloading models to free RAM.")
        self.tts.unload()
        self.translator.unload()
        self._set_status("Models unloaded (RAM freed). Will reload on next translation.")

    def _update_title_bar(self) -> None:
        """Updates the header title to reflect current provider and voice."""
        provider = self.config.get("translation_provider", "gemini").upper()
        voice = self.config.get("edge_voice", "")
        self.title = f"RU-DE Translator [{provider} + EDGE_TTS ({voice})]"

    def _set_status(self, text: str, *, error: bool = False) -> None:
        """Updates the status message widget."""
        status = self.query_one("#status-msg", Static)
        if error:
            status.update(f"[bold red]✗ {text}[/]")
        else:
            status.update(f"[cyan]{text}[/]")

    # ── Event handlers ──────────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-text":
            await self._do_translate()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        handlers = {
            "btn-translate": self._do_translate,
            "btn-speak": self.action_speak,
            "btn-practice": self._do_practice,
            "btn-export": self._do_export,
            "btn-stop": self.action_stop,
            "btn-settings": lambda: self.action_open_settings(),
        }
        handler = handlers.get(event.button.id)
        if handler:
            result = handler()
            if asyncio.iscoroutine(result):
                await result

    # ── Core actions ────────────────────────────────────────────────────

    async def _do_translate(self) -> None:
        self._reset_idle_timer()
        text = self.query_one("#input-text", Input).value.strip()
        if not text:
            self._set_status("Please enter Russian text first.", error=True)
            return

        self._set_status("Translating...")
        result_widget = self.query_one("#result-text", Static)
        result_widget.update("…")

        try:
            translation = await self.translator.translate(text)
            logger.info("Translated: '%s' → '%s'", text, translation)
            self._last_translation = translation
            result_widget.update(translation)
            self._set_status("Translation completed ✓")

            if self.config.get("auto_pronounce", True):
                await self._do_pronounce(translation)
        except TranslationError as e:
            logger.warning("Translation failed: %s", e)
            self._set_status(str(e), error=True)
            result_widget.update("")
            self._last_translation = ""
        except Exception as e:
            logger.error("Unexpected translation error", exc_info=True)
            self._set_status(f"Unexpected error: {e}", error=True)
            result_widget.update("")
            self._last_translation = ""

    async def _do_pronounce(self, text: str | None = None) -> None:
        self._reset_idle_timer()
        if text is None:
            text = self._last_translation

        if not text or not text.strip():
            self._set_status("Nothing to pronounce.", error=True)
            return

        text = text.strip()
        self._set_status("Playing audio... 🔊")
        try:
            await self.tts.speak(text)
            if not self.tts._stop_event.is_set():
                self._set_status("Playback finished ✓")
                # Record audio for export
                new_audio = (self.tts._last_audio_chunks, self.tts._last_audio_type)
                if not self.session_history or self.session_history[-1] != new_audio:
                    self.session_history.append(new_audio)
        except Exception as e:
            logger.warning("TTS failed: %s", e)
            self._set_status(str(e), error=True)
        except Exception as e:
            self._set_status(f"Practice error: {e}", error=True)
            logger.error("Unexpected practice error", exc_info=True)

    async def _do_export(self) -> None:
        if not self.session_history:
            self._set_status("Nothing to export. Translate something first.", error=True)
            return

        repeats = int(self.config.get("practice_repeats", 3))
        pause_sec = float(self.config.get("practice_pause", 2.0))
        
        self._set_status("Exporting audio... ⏳")
        
        def run_export():
            import io
            import os
            from datetime import datetime
            from pydub import AudioSegment
            
            final_audio = AudioSegment.empty()
            silence = AudioSegment.silent(duration=int(pause_sec * 1000))
            
            for chunks, audio_type in self.session_history:
                full_bytes = b"".join(chunks)
                if audio_type == "mp3":
                    audio = AudioSegment.from_file(io.BytesIO(full_bytes), format="mp3")
                elif audio_type == "pcm":
                    # Qwen PCM f32le: Need to handle float32 carefully, pydub natively prefers ints
                    audio = AudioSegment(data=full_bytes, sample_width=4, frame_rate=24000, channels=1)
                else:
                    continue
                
                for i in range(repeats):
                    final_audio += audio
                    if i < repeats - 1:
                        final_audio += silence
                
                # Pause between different phrases
                final_audio += AudioSegment.silent(duration=2000)
                
            desktop = os.path.expanduser("~/Desktop")
            filename = f"Practice_Session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp3"
            out_path = os.path.join(desktop, filename)
            final_audio.export(out_path, format="mp3")
            return out_path

        try:
            loop = asyncio.get_running_loop()
            out_path = await loop.run_in_executor(None, run_export)
            self._set_status(f"Exported to {out_path} ✓")
        except Exception as e:
            self._set_status(f"Export error: {e}", error=True)
            logger.error("Export error", exc_info=True)

    def _do_stop(self) -> None:
        self._reset_idle_timer()
        self.tts.stop()
        self._set_status("Audio stopped.")

    async def _do_practice(self) -> None:
        self._reset_idle_timer()
        if not self._last_translation:
            self._set_status("Nothing to practice.", error=True)
            return

        repeats = int(self.config.get("practice_repeats", 3))
        pause = float(self.config.get("practice_pause", 2.0))
        
        self._set_status(f"Practice mode: {repeats} repeats, {pause}s pause 🔊")
        try:
            await self.tts.practice(repeats, pause)
            self._set_status("Practice finished ✓")
        except TTSError as e:
            logger.warning("Practice failed: %s", e)
            self._set_status(str(e), error=True)
        except Exception as e:
            logger.error("Unexpected practice error", exc_info=True)
            self._set_status(f"Unexpected error: {e}", error=True)

    # ── Action bindings (for keyboard shortcuts) ────────────────────────

    def action_speak(self) -> None:
        asyncio.create_task(self._do_pronounce())

    def action_practice(self) -> None:
        asyncio.create_task(self._do_practice())

    def action_export_practice(self) -> None:
        asyncio.create_task(self._do_export())

    def action_stop(self) -> None:
        self._do_stop()

    def action_open_settings(self) -> None:
        def _on_dismiss(new_config: dict | None) -> None:
            if new_config is None:
                return
            self.config = new_config
            save_config(self.config)
            # Recreate backends with new settings
            self.translator = Translator(self.config)
            self.tts = TTSEngine(self.config)
            self._update_title_bar()
            self.notify("Settings saved ✓", severity="information")
            logger.info("Settings updated: provider=%s", self.config.get("translation_provider"))

        self.push_screen(SettingsScreen(self.config), _on_dismiss)


# ── Entry point ─────────────────────────────────────────────────────────

def main():
    setup_logging()
    _setup_excepthook()
    app = TranslatorApp()
    app.run()


if __name__ == "__main__":
    main()
