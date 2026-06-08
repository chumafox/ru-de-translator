# План адаптации RU-DE Translator для M1 Air 8GB (v2 — всё локально)

## Цель

Запустить TUI-переводчик русский→немецкий **полностью локально** на display Mac (M1 Air 8GB) с CTranslate2 (перевод) и Qwen3-TTS 0.6B 4bit (озвучка). Никаких облачных API.

## Результаты бенчмарка Qwen3-TTS 0.6B 4bit на Air

| Метрика | Значение |
|---------|----------|
| Warm gen (короткая фраза) | **3.07s** |
| Cold gen (1-й запуск) | 5.00s |
| Модель в active RAM | +314MB |
| Wired RAM пик генерации | **~2.6GB** |
| RTF warm | ~1.5x (быстрее реального времени) |

**Вывод:** влезает в 8GB. При генерации ~2.6GB wired + OS ~1.3GB + TUI остаётся ~4GB на остальное.

## Что уже есть на Air

- `.venv/` — 1.2GB, включает **torch, ctranslate2, transformers, sentencepiece, edge-tts, textual, httpx**
- Глобально: mlx, mlx-audio, transformers, sentencepiece
- Qwen3-TTS 0.6B 4bit модель в кеше (~1.6GB)

## Аудит — что мешает запуску

### 1. Жёсткие import'ы (главная проблема)

**translator.py:**
```python
import ctranslate2  # ← упадёт если нет
from transformers import AutoTokenizer  # ← упадёт если нет
```
→ Нужен try/except с флагом `CT2_AVAILABLE`

**tts.py:**
```python
from mlx_audio.tts.utils import load  # ← упадёт если нет
```
→ Нужен try/except с флагом `MLX_AVAILABLE`

### 2. Конфиг по умолчанию

Сейчас `config.py`:
- `tts_provider: "qwen_tts"` — ок, оставляем
- `ctranslate2_model_path: "~/.config/ru_de_translator/opus-zle-de-ct2"` — нужно убедиться что модель есть

### 3. CTranslate2 модель OPUS-MT (~233MB)

На pro есть: `/Users/admin/.config/ru_de_translator/opus-zle-de-ct2/`
На Air нет. Нужно скопировать.

### 4. Torch в .venv (~830MB)

CTranslate2 использует свои веса (не torch), transformers может работать без torch для токенизации. После запуска — удалить torch, освободить место.

## План

### Фаза 1: Запуск (очередность)

**Шаг 1 — Скопировать CTranslate2 модель с pro**
```bash
rsync -avz -e "ssh -i ~/.ssh/id_ed25519_headless" admin@192.168.103.70:~/.config/ru_de_translator/ ~/.config/ru_de_translator/
```

**Шаг 2 — Ленивый import CTranslate2 в translator.py**
- try/except ImportError → `CT2_AVAILABLE = False`
- Если CT2 не установлен или модель не найдена — показывать ошибку в TUI
- Сам ctranslate2 уже есть в .venv

**Шаг 3 — Ленивый import MLX в tts.py**
- try/except ImportError для `mlx_audio`
- Если MLX не установлен — показывать ошибку
- mlx-audio уже есть глобально

**Шаг 4 — Запустить и проверить**
```bash
cd ~/ru_de_translator && source .venv/bin/activate
python -m ru_de_translator
```
Перевести фразу → озвучить локально

### Фаза 2: Оптимизация

**Шаг 5 — Удалить torch из .venv (освободить 830MB)**
- `pip uninstall torch torchaudio -y`
- Убедиться что CTranslate2 + transformers работают

**Шаг 6 — Проверить memory_pressure**
```bash
memory_pressure | grep -E 'Pages (free|active|wired)'
```
Заменить idle → после загрузки модели → во время генерации

**Шаг 7 — Почистить pyproject.toml**
- Убрать torch, torchaudio, accelerate, edge-tts из обязательных
- Оставить только то что реально нужно

## Файлы для изменения

| Файл | Что меняем |
|------|------------|
| `translator.py` | try/except для ctranslate2 + transformers |
| `tts.py` | try/except для mlx_audio |
| `config.py` | проверить дефолтные пути (qwen_tts, ctranslate2 модель) |
| `app.py` | title bar — Qwen вместо Edge TTS |

## Риски

1. **Torch в .venv** — можно удалить, но `transformers.AutoTokenizer` может ругнуться. Надо проверить.
2. **CTranslate2 модель 233MB** — скопировать с pro по WiFi (медленно, но терпимо)
3. **Qwen TTS 2.6GB wired пик** — если одновременно открыт браузер + Xcode, может быть memory pressure. При обычной работе TUI один — норм.
