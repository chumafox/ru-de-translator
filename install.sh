#!/usr/bin/env bash
# ==============================================================================
# RU-DE Translator Setup Script (DevOps Style)
# Checks hardware requirements, handles dependencies, and bootstraps the project.
# ==============================================================================

set -e

# --- Configuration ---
MIN_RAM_GB=8
MIN_DISK_GB=2

# --- Helpers ---
function show_gui_error() {
    local msg="$1"
    echo -e "\033[0;31m[ERROR]\033[0m $msg"
    # Show native macOS graphical error dialog
    if [[ $(uname) == "Darwin" ]]; then
        osascript -e "display dialog \"$msg\" buttons {\"OK\"} default button \"OK\" with icon stop with title \"RU-DE Setup Error\""
    fi
    exit 1
}

function show_gui_success() {
    local msg="$1"
    echo -e "\033[0;32m[SUCCESS]\033[0m $msg"
    # Show native macOS graphical notification
    if [[ $(uname) == "Darwin" ]]; then
        osascript -e "display notification \"$msg\" with title \"RU-DE Setup\" sound name \"Glass\""
    fi
}

function print_info() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

# --- Hardware Checks ---
print_info "Running system checks..."

if [[ $(uname) == "Darwin" ]]; then
    # 1. RAM Check (macOS)
    RAM_BYTES=$(sysctl -n hw.memsize)
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
    if [ "$RAM_GB" -lt "$MIN_RAM_GB" ]; then
        show_gui_error "ОШИБКА: Недостаточно ОЗУ! У вас ${RAM_GB}GB, но для стабильной работы локальных нейросетей требуется минимум ${MIN_RAM_GB}GB."
    fi
    print_info "RAM check passed: ${RAM_GB}GB installed."

    # 2. Disk Space Check (macOS)
    # Get available space on root partition in 512-byte blocks, convert to GB
    DISK_AVAIL_BLOCKS=$(df / | tail -1 | awk '{print $4}')
    DISK_AVAIL_GB=$(( DISK_AVAIL_BLOCKS * 512 / 1024 / 1024 / 1024 ))
    if [ "$DISK_AVAIL_GB" -lt "$MIN_DISK_GB" ]; then
        show_gui_error "ОШИБКА: Мало места на SSD! Свободно ${DISK_AVAIL_GB}GB, а для загрузки моделей нужно хотя бы ${MIN_DISK_GB}GB."
    fi
    print_info "Disk check passed: ${DISK_AVAIL_GB}GB free."
else
    print_info "Non-macOS system detected. Skipping strict hardware GUI checks."
fi

# --- Dependency Checks & Installation ---
print_info "Checking required dependencies..."

# Check Homebrew
if [[ $(uname) == "Darwin" ]] && ! command -v brew &> /dev/null; then
    print_info "Homebrew not found. It is recommended to install it first: https://brew.sh/"
fi

# Check FFmpeg (required for ffplay / Edge TTS)
if ! command -v ffmpeg &> /dev/null || ! command -v ffplay &> /dev/null; then
    print_info "FFmpeg not found. Attempting to install..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        show_gui_error "Установите FFmpeg вручную! Без него не будет работать аудио. На Маке: brew install ffmpeg"
    fi
fi
print_info "FFmpeg is ready."

# Check 'uv' package manager
if ! command -v uv &> /dev/null; then
    print_info "Утилита 'uv' не найдена. Устанавливаем..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
print_info "Python package manager (uv) is ready."

# --- Bootstrapping ---
print_info "Creating virtual environment and installing python packages..."

if [ -f "pyproject.toml" ]; then
    uv sync
else
    # Fallback to pure pip if pyproject.toml isn't strict
    uv venv
    source .venv/bin/activate
    uv pip install -e .
fi

print_info "Prefetching the primary translation model from HuggingFace..."
uv run python -c "
import huggingface_hub
import sys
try:
    print('Downloading/verifying CTranslate2 model (Helsinki-NLP/opus-mt-tc-big-zle-de)...')
    huggingface_hub.snapshot_download(repo_id='Helsinki-NLP/opus-mt-tc-big-zle-de')
    print('Model is cached and ready!')
except Exception as e:
    print(f'Warning: Model pre-download failed: {e}', file=sys.stderr)
"

show_gui_success "Установка RU-DE Translator успешно завершена! Запускайте ./rude"
