import asyncio
from textual.app import App, ComposeResult
from textual.widgets import RichLog


class TestApp(App):
    def compose(self) -> ComposeResult:
        yield RichLog(markup=True)

    async def on_ready(self) -> None:
        log = self.query_one(RichLog)
        text = '[@click="speak_text(\'das ist gut\')"][underline bright_yellow]"das ist gut"[/][/]'
        try:
            log.write(f"[cyan]Qwen:[/cyan] {text}")
            print("Wrote text successfully")
        except Exception as e:
            print(f"Error writing: {e}")

        try:
            # Let's test with a newline
            text2 = '[@click="speak_text(\'das \n ist\')"][underline bright_yellow]"das \n ist"[/][/]'
            log.write(f"[cyan]Qwen:[/cyan] {text2}")
            print("Wrote text2 successfully")
        except Exception as e:
            print(f"Error writing text2: {e}")

        await asyncio.sleep(0.1)
        self.exit()


if __name__ == "__main__":
    TestApp().run()
