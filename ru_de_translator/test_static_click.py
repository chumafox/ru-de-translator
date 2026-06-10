from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll


class ChatLog(VerticalScroll):
    def add_message(self, text):
        self.mount(Static(text))
        self.scroll_end(animate=False)


class TestApp(App):
    def compose(self) -> ComposeResult:
        yield ChatLog(id="chat")

    def on_mount(self) -> None:
        chat = self.query_one("#chat", ChatLog)
        chat.add_message("[@click='test_action']CLICK ME[/]")

    def action_test_action(self) -> None:
        print("CLICK WORKS!")
        self.exit()


if __name__ == "__main__":
    app = TestApp()
    app.run()
