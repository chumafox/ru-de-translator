import asyncio
from ru_de_translator.app import TranslatorApp


async def main():
    app = TranslatorApp()
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        print("Testing direct TTS call first...")
        await app.tts.speak("Guten Tag")

        print("Testing action_speak_text...")
        app.action_speak_text("Hallo Welt")
        await pilot.pause(2.0)

        print("Done")


if __name__ == "__main__":
    asyncio.run(main())
