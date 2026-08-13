"""Asynchronous translation backends for RU-DE Translator."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
from collections.abc import Awaitable, Callable

import httpx

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when a translation attempt fails."""


_SYSTEM_PROMPT = (
    "You are a precise translator. Translate the user's Russian text to German. "
    "Output ONLY the translated German text. Do not provide explanations, notes, or introductions."
)
_USER_PROMPT_TEMPLATE = "Russian text: {text}\nGerman translation:"
_LLM_TIMEOUT = 120.0
_API_TIMEOUT = 30.0
_MAX_INPUT_CHARS = 10_000


class Translator:
    """Dispatch translation requests and lazily retain expensive local models."""

    def __init__(self, config: dict):
        self.config = config
        self._ct2_translator = None
        self._ct2_tokenizer = None
        self._ct2_signature: tuple[str, str] | None = None
        self._ct2_lock = threading.Lock()
        self._client: httpx.AsyncClient | None = None

    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                follow_redirects=False,
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        await asyncio.to_thread(self.unload)

    def unload(self) -> None:
        """Unload local models to free RAM."""
        with self._ct2_lock:
            if self._ct2_translator is not None:
                logger.info("Unloading CTranslate2 model")
            self._ct2_translator = None
            self._ct2_tokenizer = None
            self._ct2_signature = None
        import gc

        gc.collect()

    async def translate(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        if len(text) > _MAX_INPUT_CHARS:
            raise TranslationError(f"Text is too long (maximum {_MAX_INPUT_CHARS} characters).")

        dispatch: dict[str, Callable[[str], Awaitable[str]]] = {
            "gemini": self._translate_gemini,
            "ollama": self._translate_ollama,
            "lm_studio": self._translate_lm_studio,
            "translatelocally": self._translate_translatelocally,
            "ctranslate2": self._translate_ctranslate2,
        }
        provider = self.config.get("translation_provider", "ctranslate2")
        handler = dispatch.get(provider)
        if handler is None:
            raise TranslationError(f"Unknown translation provider: {provider}")
        result = (await handler(text)).strip()
        if not result:
            raise TranslationError(f"{provider} returned an empty translation.")
        return result

    async def _post_json(
        self, url: str, payload: dict, provider: str, timeout: float, headers: dict | None = None
    ) -> dict:
        try:
            response = await self._http_client().post(
                url, json=payload, headers=headers, timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("response root is not an object")
            return result
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            try:
                detail = exc.response.json().get("error", {}).get("message", detail)
            except (ValueError, AttributeError):
                pass
            raise TranslationError(
                f"{provider} error ({exc.response.status_code}): {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise TranslationError(f"Cannot connect to {provider}: {exc}") from exc
        except ValueError as exc:
            raise TranslationError(f"{provider} returned invalid JSON: {exc}") from exc

    async def _translate_gemini(self, text: str) -> str:
        api_key = self.config.get("gemini_api_key", "").strip()
        if not api_key:
            raise TranslationError("Gemini API key is not configured. Add it in Settings (F1).")
        model = self.config.get("gemini_model", "gemini-2.5-flash").strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": _USER_PROMPT_TEMPLATE.format(text=text)}]}],
            "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "generationConfig": {"temperature": 0.1},
        }
        result = await self._post_json(
            url, payload, "Gemini API", _API_TIMEOUT, {"x-goog-api-key": api_key}
        )
        candidates = result.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        if not parts:
            reason = result.get("promptFeedback", {}).get("blockReason", "no candidates")
            raise TranslationError(f"Gemini returned no translation ({reason}).")
        return "".join(part.get("text", "") for part in parts)

    async def _translate_ollama(self, text: str) -> str:
        base = self.config.get("ollama_url", "http://localhost:11434").rstrip("/")
        payload = {
            "model": self.config.get("ollama_model", "qwen2.5:3b"),
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "options": {"temperature": 0.1, "num_ctx": 1024, "num_predict": 256},
            "stream": False,
        }
        result = await self._post_json(f"{base}/api/chat", payload, "Ollama", _LLM_TIMEOUT)
        return re.sub(
            r"<think>.*?</think>", "", result.get("message", {}).get("content", ""), flags=re.S
        )

    async def _translate_lm_studio(self, text: str) -> str:
        base = self.config.get("lm_studio_url", "http://localhost:1234/v1").rstrip("/")
        payload = {
            "model": self.config.get("lm_studio_model", "local-model"),
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
            "stream": False,
        }
        result = await self._post_json(
            f"{base}/chat/completions", payload, "LM Studio", _LLM_TIMEOUT
        )
        choices = result.get("choices") or []
        return choices[0].get("message", {}).get("content", "") if choices else ""

    async def _translate_translatelocally(self, text: str) -> str:
        binary = os.path.expanduser(self.config.get("translatelocally_bin", "translateLocally"))
        model = self.config.get("translatelocally_model", "ru-de").strip()
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                binary,
                "-m",
                model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(text.encode("utf-8")), timeout=60.0
            )
        except FileNotFoundError as exc:
            raise TranslationError(f"translateLocally binary not found: '{binary}'.") from exc
        except asyncio.TimeoutError as exc:
            if process is not None:
                process.kill()
                await process.wait()
            raise TranslationError("translateLocally timed out after 60 seconds.") from exc
        except OSError as exc:
            raise TranslationError(f"translateLocally launch failed: {exc}") from exc
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()[:500]
            raise TranslationError(f"translateLocally error ({process.returncode}): {detail}")
        return stdout.decode("utf-8", errors="replace")

    async def _translate_ctranslate2(self, text: str) -> str:
        model_path = os.path.abspath(
            os.path.expanduser(self.config.get("ctranslate2_model_path", ""))
        )
        tokenizer_path = os.path.expanduser(self.config.get("ctranslate2_tokenizer_path", ""))
        if not os.path.isdir(model_path):
            raise TranslationError(
                f"CTranslate2 model folder not found at '{model_path}'. Run ./install.sh."
            )

        def sync_translate() -> str:
            try:
                import ctranslate2
                from transformers import AutoTokenizer
            except ImportError as exc:
                raise TranslationError(
                    "CTranslate2 dependencies are missing. Run: uv sync"
                ) from exc

            signature = (model_path, tokenizer_path)
            # CTranslate2 objects and unload are protected as one critical section.
            with self._ct2_lock:
                if self._ct2_signature != signature:
                    self._ct2_translator = None
                    self._ct2_tokenizer = None
                if self._ct2_translator is None:
                    logger.info("Loading CTranslate2 model from %s", model_path)
                    self._ct2_translator = ctranslate2.Translator(
                        model_path, device="cpu", compute_type="int8", inter_threads=1
                    )
                    self._ct2_tokenizer = AutoTokenizer.from_pretrained(
                        tokenizer_path, local_files_only=True
                    )
                    self._ct2_signature = signature
                tokenizer = self._ct2_tokenizer
                tokens = tokenizer.convert_ids_to_tokens(
                    tokenizer.encode(text, add_special_tokens=True)
                )
                result = self._ct2_translator.translate_batch([tokens], beam_size=2)[0]
                ids = tokenizer.convert_tokens_to_ids(result.hypotheses[0])
                return tokenizer.decode(ids, skip_special_tokens=True)

        try:
            return await asyncio.to_thread(sync_translate)
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"CTranslate2 translation failed: {exc}") from exc
