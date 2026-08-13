"""Configuration and logging for RU-DE Translator."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__version__ = "0.3.0"

CONFIG_DIR = Path(
    os.environ.get("RUDE_CONFIG_DIR", Path.home() / ".config" / "ru_de_translator")
).expanduser()
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "app.log"

DEFAULT_CONFIG: dict[str, Any] = {
    "translation_provider": "ctranslate2",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "qwen2.5:3b",
    "lm_studio_url": "http://localhost:1234/v1",
    "lm_studio_model": "local-model",
    "translatelocally_bin": "/Applications/translateLocally.app/Contents/MacOS/translateLocally",
    "translatelocally_model": "ru-de",
    "ctranslate2_model_path": str(CONFIG_DIR / "opus-zle-de-ct2"),
    "ctranslate2_tokenizer_path": str(CONFIG_DIR / "tokenizer"),
    "tts_provider": "edge_tts",
    "edge_voice": "de-DE-KatjaNeural",
    "qwen_tts_model": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit",
    "qwen_tts_voice": "ryan",
    "auto_pronounce": True,
    "practice_repeats": 3,
    "practice_pause": 2.0,
    "model_idle_timeout": 300,
    "export_dir": str(Path.home() / "Desktop"),
}

_ALLOWED_TRANSLATORS = {"gemini", "ollama", "lm_studio", "translatelocally", "ctranslate2"}
_ALLOWED_TTS = {"edge_tts", "qwen_tts"}
logger = logging.getLogger(__name__)


def normalize_config(data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Merge user values with defaults and clamp unsafe/invalid scalar settings."""
    config = DEFAULT_CONFIG.copy()
    if data:
        config.update(data)

    # Migrate the short-lived, mismatched UI key used in v0.2.
    if data and "ctranslate2_tokenizer_name" in data and "ctranslate2_tokenizer_path" not in data:
        config["ctranslate2_tokenizer_path"] = data["ctranslate2_tokenizer_name"]
    config.pop("ctranslate2_tokenizer_name", None)
    config.pop("auto_bounce", None)

    if config.get("translation_provider") not in _ALLOWED_TRANSLATORS:
        config["translation_provider"] = DEFAULT_CONFIG["translation_provider"]
    if config.get("tts_provider") not in _ALLOWED_TTS:
        config["tts_provider"] = DEFAULT_CONFIG["tts_provider"]

    try:
        config["practice_repeats"] = min(20, max(1, int(config["practice_repeats"])))
    except (TypeError, ValueError):
        config["practice_repeats"] = DEFAULT_CONFIG["practice_repeats"]
    try:
        config["practice_pause"] = min(30.0, max(0.0, float(config["practice_pause"])))
    except (TypeError, ValueError):
        config["practice_pause"] = DEFAULT_CONFIG["practice_pause"]
    try:
        config["model_idle_timeout"] = min(3600, max(30, int(config["model_idle_timeout"])))
    except (TypeError, ValueError):
        config["model_idle_timeout"] = DEFAULT_CONFIG["model_idle_timeout"]

    for key, default in DEFAULT_CONFIG.items():
        if isinstance(default, str) and not isinstance(config.get(key), str):
            config[key] = default
    config["auto_pronounce"] = bool(config.get("auto_pronounce", True))
    return config


def load_config() -> dict[str, Any]:
    """Load configuration, recovering gracefully from missing or damaged files."""
    if not CONFIG_FILE.exists():
        return normalize_config()
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        # Upgrade permissions of configs created by older versions.
        try:
            CONFIG_FILE.chmod(0o600)
        except OSError:
            logger.debug("Could not tighten config permissions", exc_info=True)
        if not isinstance(data, dict):
            raise ValueError("configuration root must be a JSON object")
        return normalize_config(data)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        logger.warning("Failed to load config, using defaults: %s", exc)
        return normalize_config()


def save_config(config: Mapping[str, Any]) -> None:
    """Atomically save normalized configuration with owner-only permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = normalize_config(config)
    temp_path: str | None = None
    try:
        fd, temp_path = tempfile.mkstemp(prefix="config-", suffix=".json", dir=CONFIG_DIR)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, CONFIG_FILE)
    except OSError as exc:
        logger.error("Error saving config: %s", exc)
        raise
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def setup_logging() -> None:
    """Configure a bounded rotating application log."""
    from logging.handlers import RotatingFileHandler

    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
