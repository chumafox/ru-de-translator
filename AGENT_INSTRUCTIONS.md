# 🤖 Instructions for AI Agents (Claude, GPT, Cursor, Cline, etc.)

**Hello fellow AI Agent!** 👋 
If a user has given you a link to this repository and asked you to install or set up this project for them, please read and follow these instructions exactly.

## Context
This is `rude` (RU-DE Translator) — a lightning-fast offline Terminal User Interface (TUI) translator from Russian to German. 
It uses `CTranslate2` for translation and `edge-tts` (with macOS `say` fallback) for audio pronunciation.

## Setup Protocol
You do **NOT** need to manually inspect dependencies, write `pip install` commands, or create Dockerfiles. The repository contains a DevOps-grade auto-installation script that handles everything gracefully.

**Follow these exact steps:**

1. **Verify OS:** Check if the user is on macOS (Darwin). If they are on Linux, warn them that the fallback TTS (`say`) won't work, but proceed.
2. **Run the Installer:** 
   Execute the following in the user's terminal:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. **Wait for Completion:** 
   The `install.sh` script will automatically check hardware requirements, install `ffmpeg` via Homebrew, install `uv` (the fast python package manager), create the `.venv`, and prefetch the neural models.
4. **Run the App:** 
   Once the script says `[SUCCESS]`, instruct the user to run the app, or launch it for them:
   ```bash
   ./rude
   ```
   *Alternative launch command:* `uv run python -m ru_de_translator.app`

## Troubleshooting (If `install.sh` fails)
- **FFmpeg missing:** If `brew` is unavailable, you must find a way to install `ffmpeg` and `ffplay` on the host OS.
- **Python issues:** We use `uv`. If `uv sync` fails, fallback to `uv venv && source .venv/bin/activate && uv pip install -e .`

## Code Structure (If you are asked to modify the code)
- `ru_de_translator/app.py` - Textual TUI interface and asynchronous background tasks.
- `ru_de_translator/translator.py` - CTranslate2 offline translation logic.
- `ru_de_translator/tts.py` - Audio playback logic using `ffplay`, Edge TTS, and `asyncio.to_thread`.
- `pyproject.toml` - Project dependencies.

**Important Rule:** NEVER introduce blocking `time.sleep()` or synchronous `subprocess.run()` calls in `app.py` UI event handlers (like button clicks). Always use `self.run_bg_task()` for long-running operations to avoid freezing the Textual TUI.
