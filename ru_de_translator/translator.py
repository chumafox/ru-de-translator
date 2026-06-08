"""Translation backends for RU-DE Translator.

Supports: Gemini API, Ollama, LM Studio, translateLocally, CTranslate2.
"""

import asyncio
import logging
import os
import threading

import httpx

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when a translation attempt fails."""


# Shared prompt for LLM-based providers
_SYSTEM_PROMPT = (
    "You are a precise translator. Translate the user's Russian text to German. "
    "Output ONLY the translated German text. "
    "Do not provide explanations, notes, or introductions."
)

_USER_PROMPT_TEMPLATE = (
    "You are a precise translator. Translate the following Russian text to German. "
    "Return ONLY the translated German text, with no explanations, no chat preamble, and no extra notes.\n\n"
    "Russian text: {text}\n"
    "German translation:"
)

# Timeout for local LLM providers (can be slow on first load)
_LLM_TIMEOUT = 120.0
# Timeout for cloud API
_API_TIMEOUT = 30.0


class Translator:
    """Strategy-pattern translator that dispatches to the configured provider."""

    def __init__(self, config: dict):
        self.config = config
        self._ct2_translator = None
        self._ct2_tokenizer = None
        self._ct2_model_path: str | None = None  # Track loaded model path
        self._ct2_lock = threading.Lock()

    def unload(self) -> None:
        """Unloads local models to free RAM."""
        with self._ct2_lock:
            if self._ct2_translator is not None:
                logger.info("Unloading CTranslate2 model to free RAM.")
                self._ct2_translator = None
                self._ct2_tokenizer = None
                import gc
                gc.collect()

    async def translate(self, text: str) -> str:
        """Translates the input Russian text to German based on config."""
        text = text.strip()
        if not text:
            return ""

        provider = self.config.get("translation_provider", "gemini")
        dispatch = {
            "gemini": self._translate_gemini,
            "ollama": self._translate_ollama,
            "lm_studio": self._translate_lm_studio,
            "translatelocally": self._translate_translatelocally,
            "ctranslate2": self._translate_ctranslate2,
        }

        handler = dispatch.get(provider)
        if handler is None:
            raise TranslationError(f"Unknown translation provider: {provider}")

        return await handler(text)

    # ── Gemini ──────────────────────────────────────────────────────────

    async def _translate_gemini(self, text: str) -> str:
        api_key = self.config.get("gemini_api_key", "").strip()
        if not api_key:
            raise TranslationError(
                "Gemini API key is not configured. Please add it in Settings (F1)."
            )

        model = self.config.get("gemini_model", "gemini-2.5-flash")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )

        payload = {
            "contents": [{"parts": [{"text": _USER_PROMPT_TEMPLATE.format(text=text)}]}],
            "generationConfig": {"temperature": 0.1},
        }

        async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.RequestError as e:
                raise TranslationError(
                    f"Network error connecting to Gemini API: {e}"
                ) from e

            if response.status_code != 200:
                try:
                    err_msg = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    err_msg = response.text
                raise TranslationError(
                    f"Gemini API error ({response.status_code}): {err_msg}"
                )

            result = response.json()
            candidates = result.get("candidates", [])
            if not candidates:
                raise TranslationError("No translation candidates returned by Gemini.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise TranslationError("Empty response body from Gemini translation.")

            return parts[0].get("text", "").strip()

    # ── Ollama ──────────────────────────────────────────────────────────

    async def _translate_ollama(self, text: str) -> str:
        base_url = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")
        model = self.config.get("ollama_model", "qwen2.5:7b")
        url = f"{base_url}/api/chat"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "options": {"temperature": 0.1},
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=_LLM_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.RequestError as e:
                raise TranslationError(
                    f"Network error connecting to Ollama at {base_url}: {e}. "
                    "Make sure Ollama is running."
                ) from e

            if response.status_code != 200:
                raise TranslationError(
                    f"Ollama error ({response.status_code}): {response.text}"
                )

            result = response.json()
            content = result.get("message", {}).get("content", "").strip()
            if not content:
                raise TranslationError("Ollama returned an empty translation.")
            return content

    # ── LM Studio ───────────────────────────────────────────────────────

    async def _translate_lm_studio(self, text: str) -> str:
        base_url = self.config.get("lm_studio_url", "http://localhost:1234/v1").rstrip("/")
        model = self.config.get("lm_studio_model", "local-model")
        url = f"{base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=_LLM_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.RequestError as e:
                raise TranslationError(
                    f"Network error connecting to LM Studio at {base_url}: {e}. "
                    "Make sure LM Studio is running and its server is active."
                ) from e

            if response.status_code != 200:
                raise TranslationError(
                    f"LM Studio error ({response.status_code}): {response.text}"
                )

            result = response.json()
            choices = result.get("choices", [])
            if not choices:
                raise TranslationError("LM Studio returned no choices.")

            content = choices[0].get("message", {}).get("content", "").strip()
            if not content:
                raise TranslationError("LM Studio returned an empty translation.")
            return content

    # ── translateLocally ────────────────────────────────────────────────

    async def _translate_translatelocally(self, text: str) -> str:
        bin_path = self.config.get("translatelocally_bin", "translateLocally").strip()
        model = self.config.get("translatelocally_model", "ru-de").strip()

        try:
            process = await asyncio.create_subprocess_exec(
                bin_path,
                "-m",
                model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=text.encode("utf-8")),
                timeout=60.0,
            )
        except FileNotFoundError:
            raise TranslationError(
                f"translateLocally binary not found at '{bin_path}'. "
                "Make sure it is installed and the path is correct in Settings. "
                "For macOS: '/Applications/translateLocally.app/Contents/MacOS/translateLocally'."
            )
        except asyncio.TimeoutError:
            raise TranslationError(
                "translateLocally timed out after 60 seconds."
            )
        except OSError as e:
            raise TranslationError(f"translateLocally launch failed: {e}") from e

        if process.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            raise TranslationError(
                f"translateLocally error (exit {process.returncode}): {err_msg}"
            )

        return stdout.decode("utf-8", errors="replace").strip()

    # ── CTranslate2 ────────────────────────────────────────────────────

    async def _translate_ctranslate2(self, text: str) -> str:
        try:
            import ctranslate2
            from transformers import AutoTokenizer
        except ImportError as e:
            raise TranslationError(
                "CTranslate2 or transformers is not installed. "
                "Run: pip install ctranslate2 transformers sentencepiece"
            ) from e

        model_path = os.path.expanduser(
            self.config.get("ctranslate2_model_path", "~/.config/ru_de_translator/opus-zle-de-ct2")
        )
        tokenizer_path = os.path.expanduser(
            self.config.get("ctranslate2_tokenizer_path", "~/.config/ru_de_translator/tokenizer")
        )

        if not os.path.isdir(model_path):
            raise TranslationError(
                f"CTranslate2 model folder not found at '{model_path}'. "
                "Please run the automatic setup or verify the path in Settings (F1)."
            )

        def _sync_translate() -> str:
            with self._ct2_lock:
                # Invalidate cached translator if the model path changed
                if self._ct2_translator is not None and self._ct2_model_path != model_path:
                    logger.info("CTranslate2 model path changed, reloading...")
                    self._ct2_translator = None
                    self._ct2_tokenizer = None
    
                if self._ct2_translator is None:
                    logger.info("Loading CTranslate2 model from %s", model_path)
                    self._ct2_translator = ctranslate2.Translator(
                        model_path,
                        device="cpu",
                        compute_type="int8",
                        inter_threads=1,
                        intra_threads=4,
                    )
                    self._ct2_tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
                    self._ct2_model_path = model_path

            tokens = self._ct2_tokenizer.convert_ids_to_tokens(
                self._ct2_tokenizer.encode(text)
            )
            results = self._ct2_translator.translate_batch([tokens])
            output_ids = self._ct2_tokenizer.convert_tokens_to_ids(
                results[0].hypotheses[0]
            )
            return self._ct2_tokenizer.decode(output_ids)

        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _sync_translate)
        except TranslationError:
            raise  # Don't re-wrap our own errors
        except Exception as e:
            raise TranslationError(f"CTranslate2 translation failed: {e}") from e
