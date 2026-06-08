# RU-DE Translator TUI

A fast, lightweight, and beautiful Terminal User Interface (TUI) tool to translate Russian words or phrases into German and pronounce them using high-quality neural Text-to-Speech (TTS).

## Features

- **Translation Backends**:
  - **CTranslate2 (OPUS-MT)** — Local, fast, offline neural translation via Helsinki-NLP `opus-mt-tc-big-zle-de` model (int8 quantized, ~74 MB). **Default and recommended.**
  - **Google Gemini API** — Cloud-based generative AI (free key required).
  - **translateLocally (OPUS-MT)** — Local, native C++ neural translation engine.
  - **Ollama** — Local LLM server (e.g., `qwen2.5:7b`).
  - **LM Studio** — Local OpenAI-compatible LLM server.
- **High-Quality Neural TTS**:
  - **Microsoft Edge TTS** — Neural, high-quality German voices, online, free, no API keys.
- **TUI Interface**:
  - Dark Catppuccin-themed design (powered by `Textual`).
  - Keyboard shortcuts for fast workflow.
  - Interactive settings screen for all providers, models, and voices.
  - Auto-pronounce on translate (configurable).

## Prerequisites

- macOS (uses `afplay` for audio playback)
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended, super-fast package runner)

## Installation & Running

### Quick start with `uv`

```bash
# From the project directory:
uv run rude

# Or from anywhere using the shell alias:
source ~/.zshrc
rude
```

### Alternative: install as a package

```bash
cd ~/ru_de_translator
uv pip install -e .
rude          # now available globally
```

### Running as a module

```bash
uv run python -m ru_de_translator
```

## Keyboard Controls

| Key         | Action                          |
|-------------|---------------------------------|
| `Enter`     | Submit Russian text for translation |
| `F1`        | Open Settings Screen            |
| `Ctrl + P`  | Speak (re-pronounce) the translated text |
| `Ctrl + S`  | Stop audio playback             |
| `Ctrl + Q`  | Quit the application            |

## Configuration

All settings are stored in `~/.config/ru_de_translator/config.json`.

Press **`F1`** inside the app to configure:

1. **Translation Provider** — Choose between CTranslate2, Gemini, translateLocally, Ollama, LM Studio.
2. **CTranslate2 Settings** — Model path and HuggingFace tokenizer name.
3. **Gemini API Key** — Masked for privacy.
4. **Ollama / LM Studio** — URL and model names for local LLM servers.
5. **translateLocally** — Binary path and model name.
6. **German Voice** — Select from available Edge TTS neural voices.
7. **Auto Pronounce** — Toggle automatic pronunciation after translation.

## Logs

Application logs are written to `~/.config/ru_de_translator/app.log`.

## Project Structure

```
ru_de_translator/
├── __init__.py          # Package marker
├── __main__.py          # python -m ru_de_translator entry point
├── app.py               # Textual TUI application
├── config.py            # Configuration loading/saving/logging
├── translator.py        # Translation backends (5 providers)
├── tts.py               # Edge TTS engine
├── style.tcss           # Catppuccin-themed TUI styles
├── pyproject.toml       # Project metadata & dependencies
└── README.md
```
