import asyncio
import time
from ru_de_translator.app import TranslatorApp
from textual.widgets import Input, Static


async def test():
    app = TranslatorApp()
    app.config["translation_provider"] = "ctranslate2"
    app.config["tts_provider"] = "edge_tts"
    app.config["auto_pronounce"] = True
    app.config["practice_repeats"] = 3
    app.config["practice_pause"] = 1.0

    async with app.run_test() as pilot:
        await asyncio.sleep(1)

        # Type and translate
        app.query_one("#input-text", Input).value = "Guten Tag"
        await pilot.press("enter")

        status_widget = app.query_one("#status-msg", Static)

        # Wait for auto-pronounce to finish
        while "playback finished" not in str(status_widget.render()).lower():
            await asyncio.sleep(0.1)

        print("Auto-pronounce done.")

        # Trigger practice
        print("Starting practice...")
        start_time = time.time()
        await pilot.press("ctrl+r")

        while "practice finished" not in str(status_widget.render()).lower():
            if (
                "error" in str(status_widget.render()).lower()
                or "failed" in str(status_widget.render()).lower()
            ):
                print("Error:", status_widget.render())
                break
            await asyncio.sleep(0.1)

        duration = time.time() - start_time
        print(f"Practice duration: {duration:.2f}s")
        print("Final status:", status_widget.render())


if __name__ == "__main__":
    asyncio.run(test())
