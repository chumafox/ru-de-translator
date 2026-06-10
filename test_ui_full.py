import asyncio
from ru_de_translator.app import TranslatorApp
from textual.widgets import Input, RichLog


async def run_test():
    app = TranslatorApp()
    async with app.run_test() as pilot:
        await asyncio.sleep(0.5)

        # Open chat drawer directly
        app.action_toggle_chat()
        await asyncio.sleep(0.5)

        # Focus input and type
        chat_input = app.query_one("#chat-input", Input)
        chat_input.focus()
        chat_input.value = "Hallo, wie geht es dir?"

        # Press enter
        await pilot.press("enter")
        await asyncio.sleep(1)

        log = app.query_one("#chat-log", RichLog)
        lines = [line.text for line in log.lines]
        print("UI State after enter:")
        print("\n".join(lines))

        if "Qwen: ⏳ Thinking..." not in "\n".join(lines):
            print("ERROR: on_input_submitted was NOT triggered!")
            return

        print("Waiting for response...")
        for _ in range(60):
            lines = [line.text for line in log.lines]
            full_text = "\n".join(lines)
            if (
                "Thinking..." not in full_text
                and "Qwen:" in full_text
                and len(lines) > 2
            ):
                print("SUCCESS! LLM Responded!")
                print(full_text)

                # Now test if the action_speak_text can be called directly
                print("Testing action_speak_text...")
                app.action_speak_text("Hallo")
                await asyncio.sleep(1)
                print("Speak action finished.")
                return

            await asyncio.sleep(0.5)

        print("Timeout! LLM never responded.")


if __name__ == "__main__":
    asyncio.run(run_test())
