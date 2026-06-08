"""Configuration management for RU-DE Translator.

Stores configuration in ~/.config/ru_de_translator/config.json.
Stores logs in ~/.config/ru_de_translator/app.log.
"""

import json
import logging
from pathlib import Path

__version__ = "0.2.0"

CONFIG_DIR = Path.home() / ".config" / "ru_de_translator"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "app.log"

DEFAULT_CONFIG = {
    "translation_provider": "ctranslate2",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "qwen2.5:3b",
    "lm_studio_url": "http://localhost:1234/v1",
    "lm_studio_model": "local-model",
    "translatelocally_bin": "/Applications/translateLocally.app/Contents/MacOS/translateLocally",
    "translatelocally_model": "ru-de",
    "ctranslate2_model_path": "~/.config/ru_de_translator/opus-zle-de-ct2",
    "ctranslate2_tokenizer_path": "~/.config/ru_de_translator/tokenizer",
    "tts_provider": "edge_tts",
    "edge_voice": "de-DE-KatjaNeural",
    "qwen_tts_model": "/Users/jenyanovak/.cache/huggingface/hub/models--mlx-community--Qwen3-TTS-12Hz-0.6B-Base-4bit",
    "qwen_tts_voice": "ryan",
    "auto_pronounce": True,
    "practice_repeats": 3,
    "practice_pause": 2.0,
}

# Keys that should NOT be persisted (internal runtime keys)
_INTERNAL_KEYS = frozenset()

logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Loads configuration from file, merging with defaults for missing keys."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge: defaults as base, user data on top
        config = DEFAULT_CONFIG.copy()
        config.update(data)
        # Remove any legacy keys
        config.pop("auto_bounce", None)
        return config
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load config, using defaults: %s", e)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Saves configuration to file. Creates directory if needed."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Filter out internal keys before saving
        data = {k: v for k, v in config.items() if k not in _INTERNAL_KEYS}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except OSError as e:
        logger.error("Error saving config: %s", e)


def setup_logging() -> None:
    """Configures logging to write to the config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
