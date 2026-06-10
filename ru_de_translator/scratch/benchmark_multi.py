"""Multi-iteration E2E benchmark: validates consistent hot-path latency."""

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

    # Warm-up
    print("Warming up...")
    await translator.translate("тест")
    await tts.speak("Test.")
    await asyncio.sleep(0.3)
    print("Models loaded.\n")

    phrases = [
        "Доброе утро",
        "Доброе утро",
        "Доброе утро",
    ]

    results = []
    for i, phrase in enumerate(phrases):
        t_start = time.perf_counter()
        translation = await translator.translate(phrase)
        t_trans = time.perf_counter() - t_start

        t_tts_start = time.perf_counter()
        await tts.speak(translation)
        t_tts = time.perf_counter() - t_tts_start

        t_total = time.perf_counter() - t_start
        results.append(t_total)
        print(
            f"Run {i + 1}: '{phrase}' → '{translation}'  |  "
            f"translate={t_trans * 1000:.0f}ms  tts={t_tts * 1000:.0f}ms  total={t_total * 1000:.0f}ms"
        )
        await asyncio.sleep(0.3)

    avg = sum(results) / len(results) * 1000
    print(f"\nAverage E2E: {avg:.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
