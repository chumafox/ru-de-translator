from textual.app import App, ComposeResult
from textual.widgets import RichLog


class TestApp(App):
    def compose(self) -> ComposeResult:
        yield RichLog(markup=True)

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.write("[@click='test_action']CLICK ME[/]")

    def action_test_action(self) -> None:
        with open("click_works.txt", "w") as f:
            f.write("YES")


if __name__ == "__main__":
    app = TestApp()

    # We can't easily click in headless without a complex pilot, but let's try
    async def auto_run():
        async with app.run_test() as pilot:
            await pilot.pause(0.5)
            # simulate click? textual doesn't easily let us click a specific text span.
            pass
