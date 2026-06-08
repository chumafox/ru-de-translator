import asyncio
import time
from pathlib import Path

from translator import Translator
from tts import TTSEngine

async def main():
    print("Initializing Engines...")
    t0 = time.perf_counter()
    
    # Initialize translator
    config = {
        "translation_provider": "ctranslate2",
        "model_dir": "opus-ru-de-ct2",
        "qwen_tts_model": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
        "qwen_tts_voice": "Chelsie",
        "tts_provider": "qwen_tts"
    }
    
    translator = Translator(config)
    tts = TTSEngine(config)
    
    # Load model (warmup)
    print("Warming up translation model...")
    await translator.translate("Привет")
    
    # Run the test
    text = "Доброе утро"
    print(f"\n--- Starting E2E Test ---")
    print(f"Input: {text}")
    
    start_time = time.perf_counter()
    
    # Step 1: Translate
    translation = await translator.translate(text)
    translation_time = time.perf_counter() - start_time
    
    print(f"Translation: {translation}")
    print(f"Translation latency: {translation_time*1000:.1f} ms")
    
    # Step 2: TTS
    print("Starting TTS playback...")
    tts_start = time.perf_counter()
    await tts.speak(translation)
    tts_time = time.perf_counter() - tts_start
    
    total_time = time.perf_counter() - start_time
    print(f"TTS playback total time (includes streaming wait): {tts_time*1000:.1f} ms")
    print(f"Total E2E time: {total_time*1000:.1f} ms")
    print("--- Done ---")

if __name__ == "__main__":
    asyncio.run(main())
