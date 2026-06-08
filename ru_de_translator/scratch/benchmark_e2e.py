"""E2E benchmark: Translation + TTS with model warm-up.
Measures the HOT path (model already loaded) for "Доброе утро".
"""
import asyncio
import time
import sys
sys.path.insert(0, ".")

from translator import Translator
from tts import TTSEngine

async def main():
    config = {
        "translation_provider": "ctranslate2",
        "model_dir": "opus-ru-de-ct2",
        "qwen_tts_model": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
        "qwen_tts_voice": "Chelsie",
        "tts_provider": "qwen_tts",
    }

    translator = Translator(config)
    tts = TTSEngine(config)

    # ── Warm-up: load all models ──
    print("=== Warming up models ===")
    t0 = time.perf_counter()
    await translator.translate("тест")
    print(f"  Translation model ready: {(time.perf_counter()-t0)*1000:.0f}ms")

    t0 = time.perf_counter()
    await tts.speak("Test.")
    print(f"  TTS model ready: {(time.perf_counter()-t0)*1000:.0f}ms")

    # Wait a moment for audio to finish
    await asyncio.sleep(0.5)

    # ── Hot-path test ──
    text = "Доброе утро"
    print(f"\n=== HOT-PATH E2E Test ===")
    print(f"Input: {text}")

    t_start = time.perf_counter()

    # Step 1: Translate
    translation = await translator.translate(text)
    t_translate = time.perf_counter() - t_start
    print(f"Translation: {translation}")
    print(f"  Translation: {t_translate*1000:.1f}ms")

    # Step 2: TTS (model already loaded)
    t_tts_start = time.perf_counter()
    await tts.speak(translation)
    t_tts = time.perf_counter() - t_tts_start

    t_total = time.perf_counter() - t_start

    print(f"  TTS (hot): {t_tts*1000:.1f}ms")
    print(f"  Total E2E: {t_total*1000:.1f}ms")

if __name__ == "__main__":
    asyncio.run(main())
