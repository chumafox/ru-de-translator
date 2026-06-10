import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll


class MockApp(App):
    def __init__(self):
        super().__init__()
        self.clicked_text = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="chat-log"):
            yield Static(
                "[@click=app.speak_text('Hallo Welt')]\"Hallo Welt\"[/]",
                id="clickable-static",
            )

    def action_speak_text(self, text: str) -> None:
        self.clicked_text = text


async def test_click():
    app = MockApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.5)
        # Click the static widget
        await pilot.click("#clickable-static")
        await pilot.pause(0.5)

        if app.clicked_text == "Hallo Welt":
            print("SUCCESS: action_speak_text was triggered with 'Hallo Welt'!")
        else:
            print(
                f"FAILED: action_speak_text was NOT triggered. Value is: {app.clicked_text}"
            )


if __name__ == "__main__":
    asyncio.run(test_click())
