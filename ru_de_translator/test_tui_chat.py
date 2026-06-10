import asyncio
from ru_de_translator.app import TranslatorApp
from textual.widgets import RichLog


async def main():
    app = TranslatorApp()
    async with app.run_test(size=(120, 40)) as pilot:
        print("Opening chat drawer...")
        await pilot.press("alt+d")
        await pilot.pause(0.5)

        # Manually trigger the chat submission
        app.fetch_chat_response(
            "Ich bin ein gutes Buch gelesen. Проверь мою грамматику."
        )

        # Wait for response (poll the log)
        log = app.query_one("#chat-log", RichLog)

        print("Waiting for LLM response (up to 30 seconds)...")
        for _ in range(60):
            lines = [line.text for line in log.lines]
            full_text = "\n".join(lines)
            if (
                "Thinking..." not in full_text
                and "Qwen:" in full_text
                and len(lines) > 2
            ):
                print("\n--- CHAT LOG RESULT ---")
                print(full_text)

            print(line.text)


if __name__ == "__main__":
    asyncio.run(main())
