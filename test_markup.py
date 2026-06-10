from textual.app import App, ComposeResult
from textual.widgets import RichLog


class TestApp(App):
    def compose(self) -> ComposeResult:
        yield RichLog(markup=True)

    def on_ready(self) -> None:
        log = self.query_one(RichLog)
        log.write("Click [@click=\"speak('hello_world')\"]here[/] to speak.")

    def action_speak(self, text: str) -> None:
        print(f"Action speak called with: {text}")
        self.exit()


if __name__ == "__main__":
    TestApp().run()
