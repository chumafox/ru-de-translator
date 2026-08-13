# RU-DE Translator (`rude`)

Быстрый TUI-переводчик с русского на немецкий с озвучкой, режимом повторения и экспортом аудио.

## Возможности

- локальный перевод через **CTranslate2 + OPUS-MT** (по умолчанию);
- альтернативные провайдеры: Gemini, Ollama, LM Studio и translateLocally;
- потоковая озвучка через **Edge TTS** и локальная Qwen/MLX на Apple Silicon;
- повтор фразы с настраиваемыми паузами;
- LRU-кэш озвучки и автоматическое освобождение моделей после простоя;
- экспорт тренировочной сессии в MP3;
- отзывчивый интерфейс на Textual: модель и аудио не блокируют event loop.

## Требования

- Python 3.10+;
- `ffplay`/FFmpeg;
- около 2 ГБ свободного места для окружения и локальной модели;
- macOS или Linux. Встроенный fallback `say` доступен только на macOS.

Локальная Qwen TTS является **опциональной** и поддерживается только на Mac с Apple Silicon. Edge TTS требует интернет, а CTranslate2 после установки работает офлайн.

## Установка

```bash
git clone https://github.com/chumafox/ru-de-translator.git
cd ru-de-translator
chmod +x install.sh
./install.sh
./rude
```

Скрипт устанавливает Python-зависимости через `uv`, а затем скачивает токенизатор и конвертирует OPUS-MT в int8 CTranslate2. Повторный запуск безопасен: готовая модель не скачивается заново.

Полезные режимы установки:

```bash
# Не загружать модель сейчас
RUDE_SKIP_MODELS=1 ./install.sh

# Добавить локальную Qwen/MLX TTS (только Apple Silicon)
RUDE_INSTALL_QWEN=1 ./install.sh
```

На Debian/Ubuntu FFmpeg можно установить командой `sudo apt install ffmpeg`. На macOS установщик использует Homebrew, если `ffplay` отсутствует.

## Управление

| Клавиша | Действие |
|---|---|
| `Enter` | Перевести |
| `Ctrl+P` | Озвучить перевод |
| `Alt+R` | Режим практики |
| `Ctrl+S` | Остановить звук |
| `Ctrl+E` | Экспортировать аудио |
| `F1` | Настройки |
| `Ctrl+Q` | Выход |

Настройки сохраняются атомарно с правами владельца в `~/.config/ru_de_translator/config.json`. Ротируемый лог находится рядом в `app.log`.

## Провайдеры

### CTranslate2

Провайдер по умолчанию. `./install.sh` создаёт:

- `~/.config/ru_de_translator/opus-zle-de-ct2` — int8-модель;
- `~/.config/ru_de_translator/tokenizer` — локальный токенизатор.

### Gemini

Укажите API-ключ и модель в настройках. Ключ передаётся заголовком `x-goog-api-key`, а не в URL.

### Ollama / LM Studio

Приложение подключается только к указанному URL и **не запускает серверы автоматически**. Запустите выбранный сервер самостоятельно.

### TTS

Edge TTS включён по умолчанию. Синтезированный звук кэшируется в памяти для быстрых повторов. Qwen загружается лениво и не влияет на установку/запуск на Linux и Intel Mac.

## Разработка

```bash
uv sync --extra dev
uv run pytest
uv run ruff check ru_de_translator/app.py ru_de_translator/config.py \
  ru_de_translator/translator.py ru_de_translator/tts.py tests scripts
uv run ruff format --check ru_de_translator/app.py ru_de_translator/config.py \
  ru_de_translator/translator.py ru_de_translator/tts.py tests scripts
```

Код приложения:

- `ru_de_translator/app.py` — Textual UI и жизненный цикл задач;
- `ru_de_translator/translator.py` — переводчики;
- `ru_de_translator/tts.py` — синтез, воспроизведение и кэш;
- `ru_de_translator/config.py` — валидация, миграция и безопасная запись настроек;
- `scripts/setup_models.py` — подготовка локальной модели;
- `tests/` — изолированные unit-тесты без сети и моделей.

Подробные результаты технического аудита: [AUDIT.md](AUDIT.md).
