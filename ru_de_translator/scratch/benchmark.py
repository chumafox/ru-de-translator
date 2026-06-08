import asyncio
import time
from ru_de_translator.config import load_config
from ru_de_translator.translator import Translator
from ru_de_translator.tts import TTSEngine

async def run_benchmark():
    print("Loading config...")
    config = load_config()
    config["tts_provider"] = "qwen_tts"
    
    translator = Translator(config)
    tts = TTSEngine(config)
    
    phrase = "Привет!"
    long_phrase = "Я очень люблю программировать на Python каждый день."
    
    print("-" * 50)
    print("WARMING UP MODELS (Cold start)...")
    start_t0 = time.perf_counter()
    res_warm = await translator.translate(phrase)
    end_t0 = time.perf_counter()
    print(f"Translation warm-up took: {(end_t0 - start_t0):.2f}s")

    start_tts0 = time.perf_counter()
    await tts.speak(res_warm)
    end_tts0 = time.perf_counter()
    print(f"TTS warm-up took (including playback): {(end_tts0 - start_tts0):.2f}s")
    
    print("-" * 50)
    print("HOT TEST (Models in RAM)...")
    
    # Translation
    start_t1 = time.perf_counter()
    res2 = await translator.translate(long_phrase)
    end_t1 = time.perf_counter()
    print(f"Hot Translation: '{res2}'")
    print(f"Translation Time taken: {(end_t1 - start_t1) * 1000:.2f} ms")

    # TTS Synthesis and Playback
    print(f"\nSynthesizing and playing hot audio...")
    start_t2 = time.perf_counter()
    await tts.speak(res2)
    end_t2 = time.perf_counter()
    print(f"TTS Hot Time (including playback): {(end_t2 - start_t2):.2f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
