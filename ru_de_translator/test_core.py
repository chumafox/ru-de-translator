import asyncio
import time
import os
import resource
import traceback

from ru_de_translator.config import load_config
from ru_de_translator.translator import Translator
from ru_de_translator.tts import TTSEngine

def get_memory_mb():
    """Returns memory usage of current process in MB (macOS ru_maxrss is in bytes)"""
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # on macOS, ru_maxrss is in bytes. On Linux it's in KB. 
    import sys
    if sys.platform == 'darwin':
        return usage / (1024 * 1024)
    else:
        return usage / 1024

async def run_tests():
    print(f"[INIT] Starting test suite. Base memory: {get_memory_mb():.1f} MB")
    
    config = load_config()
    # Force use of local models for test
    config["translation_provider"] = "ctranslate2"
    config["tts_provider"] = "edge_tts"
    
    translator = Translator(config)
    tts = TTSEngine(config)
    
    # Warmup
    print("[TEST] Warming up TTS...")
    start_t = time.time()
    await tts.warmup()
    print(f"[TEST] Warmup done in {time.time()-start_t:.2f}s. Memory: {get_memory_mb():.1f} MB")

    test_phrases = [
        "Привет", # very short
        "Как дела?", # short
        "Я хочу заказать пиццу и выпить кофе.", # medium
        "Вчера я ходил в магазин и купил много продуктов для ужина.", # medium-long
        "Германия — это страна в Центральной Европе, известная своей богатой историей и культурой.", # long
        "Где здесь ближайшая аптека?",
        "Пожалуйста, помогите мне найти дорогу к железнодорожному вокзалу.",
        "Я не говорю по-немецки, вы говорите по-английски?",
        "Спасибо большое за вашу помощь!",
        "Завтра утром я планирую поехать в Берлин на поезде." # 10th
    ]

    for i, phrase in enumerate(test_phrases, 1):
        print(f"\n--- Iteration {i}/10 ---")
        print(f"Input: {phrase}")
        
        # 1. Test translation
        start_t = time.time()
        try:
            translation = await translator.translate(phrase)
            trans_time = time.time() - start_t
            print(f"Translation: {translation} (took {trans_time:.2f}s)")
        except Exception as e:
            print(f"[ERROR] Translation failed: {e}")
            traceback.print_exc()
            return False

        # 2. Test TTS Pronounce
        print("Pronouncing...")
        start_t = time.time()
        try:
            await tts.speak(translation)
            tts_time = time.time() - start_t
            print(f"Pronounce finished. Took {tts_time:.2f}s")
        except Exception as e:
            print(f"[ERROR] TTS speak failed: {e}")
            traceback.print_exc()
            return False
            
        # 3. Test caching / repeat (Practice simulation)
        print("Practicing (from cache)...")
        start_t = time.time()
        try:
            # wait 1s
            await asyncio.sleep(1)
            # Practice method uses the cached chunks
            await tts.practice(repeats=2, pause=0.5)
            prac_time = time.time() - start_t
            print(f"Practice finished. Took {prac_time:.2f}s")
        except Exception as e:
            print(f"[ERROR] TTS practice failed: {e}")
            traceback.print_exc()
            return False

        print(f"Memory after iter {i}: {get_memory_mb():.1f} MB")
        
    print("\n--- Testing Unload ---")
    tts.unload()
    translator.unload()
    print(f"Memory after unload: {get_memory_mb():.1f} MB")
    
    print("\n[SUCCESS] All 10 iterations passed successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    if not success:
        import sys
        sys.exit(1)
