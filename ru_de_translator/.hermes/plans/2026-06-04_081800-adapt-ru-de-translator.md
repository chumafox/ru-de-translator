# План: Адаптация RU-DE Translator под наше железо

## Цель

Сделать переводчик русский→немецкий работающим на display Mac (M1 Air, 8GB) лёгким и быстрым, с возможностью использовать pro (M1 Pro, 32GB) как тяжёлый бэкенд для перевода.

## Контекст / допущения

- **Display Mac** (dispo): M1 Air 8GB — память в обрез (memory_pressure, мин 200MB)
- **Pro** (безголовый): M1 Pro 32GB — есть LM Studio + Ollama
- **Связь**: Thunderbolt Bridge (192.168.2.x) — быстрая локальная сеть
- Проект скопирован с pro на display Mac: `/Users/jenyanovak/ru_de_translator/`

## Проблемы текущего кода на M1 Air 8GB

1. **`pyproject.toml` требует torch / torchaudio / transformers / ctranslate2** — это >1GB зависимостей ради одного optional провайдера. Torch один ~830MB.
2. **TTS по умолчанию — Qwen3-TTS через MLX** — загрузка модели 0.6-1.7B в память. На 8GB это катастрофа.
3. **pyaudio** для стриминга аудио — сложнее чем просто `afplay` с temp-файлом.
4. **Настройки заточены под pro** — пути к моделям, провайдеры.
5. **Нет удалённого бэкенда** — нет варианта "перевести на pro через HTTP".

## Предлагаемый подход

### Фаза 1: Лёгкий запуск на display Mac (главное)

**Сделать все тяжёлые зависимости опциональными (ленивый import).**

Базовый набор для 90% сценариев:
- `textual` — TUI
- `httpx` — HTTP
- `edge-tts` — голос (онлайн, бесплатно, без API ключа)

```python
# В translator.py — LazyOptionalProvider паттерн для CTranslate2
try:
    import ctranslate2
    CT2_AVAILABLE = True
except ImportError:
    CT2_AVAILABLE = False
```

**Изменить дефолтный TTS с Qwen3-TTS на Edge TTS.**
- Поменять `DEFAULT_CONFIG["tts_provider"] = "edge_tts"`
- Qwen3-TTS оставить как опцию для тех, кто хочет локально (на pro)

**Почистить pyproject.toml:**
- Убрать `torch`, `torchaudio`, `accelerate` из обязательных
- Сделать `ctranslate2`, `transformers`, `sentencepiece`, `sacremoses` — optional (extra group `[ct2]`)
- Сделать `qwen-tts`, `mlx-audio`, `pyaudio`, `soundfile` — optional (extra group `[qwen]`)
- Базовые: только `textual`, `httpx`, `edge-tts`

**Исправить title-bar** — Edge TTS не голос, а провайдер.

**Файлы для изменения:**
- `pyproject.toml` — dependency groups
- `translator.py` — lazy import CTranslate2
- `tts.py` — lazy import Qwen3-TTS/MLX
- `config.py` — default TTS → edge_tts
- `app.py` — title bar формат

### Фаза 2: Pro как удалённый бэкенд

**Добавить провайдер "pro" в translator.py.**
- HTTP-клиент, шлёт запрос на pro через TB Bridge
- Прокси на pro: Ollama (11434) или LM Studio (1234/v1)
- Пользователь настраивает IP pro и порт в Settings

```python
async def _translate_pro(self, text: str) -> str:
    # POST http://192.168.2.2:11434/api/chat — Ollama на pro
    # Или http://192.168.2.2:1234/v1/chat/completions — LM Studio
```

**Файлы для изменения:**
- `translator.py` — новый провайдер "pro_ollama" / "pro_lm_studio"
- `config.py` — дефолты для pro IP/порт/модель
- `app.py` — новый пункт в Select провайдеров
- `config.py` — добавить поля `pro_url`, `pro_model`

### Фаза 3: Тюнинг под 8GB

- Проверить memory_pressure при запуске с Edge TTS + CTranslate2
- Если CTranslate2 даже в int8 жрёт >200MB — перейти на pro backend по умолчанию
- Подумать над auto-download OPUS-MT модели (74MB) при первом запуске CTranslate2

## Файлы, которые могут измениться

| Файл | Фаза | Что меняем |
|------|------|------------|
| `pyproject.toml` | 1 | Dependency groups, убрать torch из обязательных |
| `config.py` | 1,2 | Default TTS → edge_tts, new pro fields |
| `translator.py` | 1,2 | Lazy CT2 import, `_translate_pro` provider |
| `tts.py` | 1 | Lazy MLX/Qwen import |
| `app.py` | 1,2 | Title bar, provider list |
| `app.py` | 2 | Settings screen — новый блок Pro backend |

## Тесты / валидация

После каждой фазы:
```bash
cd ~/ru_de_translator
python -m ru_de_translator   # запуск TUI
# Перевести фразу, проверить произношение
# Переключить провайдер в F1, проверить
```

После Фазы 2:
```bash
# На pro: curl http://192.168.2.2:11434/api/chat (Ollama)
curl -X POST http://192.168.2.2:11434/api/chat \
  -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"translate to german: привет"}]}'
```

## Риски / open questions

- Edge TTS требует интернет (Ship WiFi — может быть нестабильным). Через китайские ограничения Edge TTS работает? Надо проверить.
- CTranslate2 + transformers даже с lazy import — если пользователь выберет CTranslate2, torch всё равно загрузится. Решение: `pip install ru-de-translator[ct2]` отдельно.
- Qwen3-TTS — возможно, стоит оставить только для pro, не тащить на display Mac.
- `translateLocally` провайдер — удалить? Он для macOS x86_64 бинарника, на ARM не работает нативно.
