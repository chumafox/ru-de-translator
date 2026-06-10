import asyncio
import time
import psutil
import os

from ru_de_translator.app import TranslatorApp
from textual.widgets import Input, Static

phrases = [
    "Привет",
    "Как дела?",
    "Я хочу заказать пиццу и выпить кофе.",
    "Вчера я ходил в магазин и купил много продуктов для ужина.",
    "Германия — это страна в Центральной Европе, известная своей богатой историей и культурой.",
    "Где здесь ближайшая аптека?",
    "Пожалуйста, помогите мне найти дорогу к железнодорожному вокзалу.",
    "Я не говорю по-немецки, вы говорите по-английски?",
    "Спасибо большое за вашу помощь!",
    "Завтра утром я планирую поехать в Берлин на поезде.",
]


async def run_tui_test():
    app = TranslatorApp()

    # Configure to ensure fast tests using current defaults
    app.config["translation_provider"] = "ctranslate2"
    app.config["tts_provider"] = "edge_tts"
    app.config["auto_pronounce"] = True
    app.config["practice_repeats"] = 1
    app.config["practice_pause"] = 0.5

    process = psutil.Process(os.getpid())
    base_memory = process.memory_info().rss / 1024 / 1024
    print(f"[INIT] Starting TUI test suite. Base memory: {base_memory:.1f} MB")

    async with app.run_test() as pilot:
        status_widget = app.query_one("#status-msg", Static)
        result_widget = app.query_one("#result-text", Static)
        input_widget = app.query_one("#input-text", Input)

        # Wait for initial model warmup (async task in app.py)
        await asyncio.sleep(1)

        for i, phrase in enumerate(phrases, 1):
            print(f"\n--- Iteration {i}/10 ---")
            print(f"Input: {phrase}")

            input_widget.value = phrase
            start_time = time.time()

            await pilot.press("enter")

            # Wait for translation to complete
            while app._last_translation == "" or app._last_translation == str(phrase):
                status_text = str(status_widget.render()).lower()
                if "error" in status_text or "failed" in status_text:
                    raise RuntimeError(f"Translation failed: {status_text}")
                # Break if translation is done or audio is playing (meaning translation finished)
                if "completed" in status_text or "playing audio" in status_text:
                    break
                await asyncio.sleep(0.1)

            translation = app._last_translation
            translation_time = time.time() - start_time
            print(
                f"Translation: {translation} (took {translation_time:.2f}s, includes TTS if auto)"
            )

            # Wait for TTS Playback to finish
            while "playback finished" not in str(status_widget.render()).lower():
                status_text = str(status_widget.render()).lower()
                if "error" in status_text or "failed" in status_text:
                    raise RuntimeError(f"TTS failed: {status_text}")
                await asyncio.sleep(0.1)

            print("TTS Auto-Pronounce finished.")

            # Practice
            print("Practicing (Ctrl+R)...")
            start_practice = time.time()
            await pilot.press("ctrl+r")

            # Wait for Practice to finish
            while "practice finished" not in str(status_widget.render()).lower():
                status_text = str(status_widget.render()).lower()
                if "error" in status_text or "failed" in status_text:
                    raise RuntimeError(f"Practice failed: {status_text}")
                await asyncio.sleep(0.1)

            practice_time = time.time() - start_practice
            print(f"Practice finished. Took {practice_time:.2f}s")

            mem = process.memory_info().rss / 1024 / 1024
            print(f"Memory after iter {i}: {mem:.1f} MB")

        print("\n[SUCCESS] All 10 TUI iterations passed successfully!")


if __name__ == "__main__":
    asyncio.run(run_tui_test())
