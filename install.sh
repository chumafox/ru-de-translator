#!/usr/bin/env bash
# Reproducible installer for RU-DE Translator.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

info() { printf '\033[0;34m[INFO]\033[0m %s\n' "$*"; }
success() { printf '\033[0;32m[SUCCESS]\033[0m %s\n' "$*"; }
fail() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

command -v curl >/dev/null || fail "Не найден curl. Установите его и повторите запуск."

if ! command -v ffplay >/dev/null; then
    if [[ "$(uname -s)" == "Darwin" ]] && command -v brew >/dev/null; then
        info "Устанавливаю ffmpeg через Homebrew..."
        brew install ffmpeg
    else
        fail "Не найден ffplay. Установите FFmpeg (например: sudo apt install ffmpeg)."
    fi
fi

if ! command -v uv >/dev/null; then
    info "Устанавливаю менеджер пакетов uv..."
    curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
command -v uv >/dev/null || fail "uv установлен, но не найден в PATH. Перезапустите shell."

SYNC_ARGS=()
if [[ "${RUDE_INSTALL_QWEN:-0}" == "1" ]]; then
    if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
        fail "Qwen/MLX поддерживается только на Apple Silicon."
    fi
    SYNC_ARGS+=(--extra qwen)
fi

info "Создаю окружение и устанавливаю зависимости..."
uv sync "${SYNC_ARGS[@]}"

if [[ "${RUDE_SKIP_MODELS:-0}" != "1" ]]; then
    info "Подготавливаю локальную int8-модель перевода (первый запуск может занять время)..."
    uv run python scripts/setup_models.py
else
    info "Загрузка модели пропущена (RUDE_SKIP_MODELS=1)."
fi

chmod +x "$ROOT_DIR/rude"
success "Готово. Запуск: ./rude"
