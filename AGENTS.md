# Contributor notes

- Run commands from the repository root.
- Install development dependencies with `uv sync --extra dev`.
- Run checks with `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .`.
- Keep blocking model, subprocess, and audio work outside Textual event handlers (`asyncio.to_thread` or a background task).
- Qwen/MLX is optional and supported only on Apple Silicon; imports must remain lazy.
- Never commit models, generated audio, logs, API keys, or local configuration.
