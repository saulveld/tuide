from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

class TUIDEApp(App):
    TITLE = "TUIDE - Terminal IDE"
    BINDINGS = [
        ("q", "quit", "Quit")
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        # We'll add more UI components here later
        yield Footer()

if __name__ == "__main__":
    app = TUIDEApp()
    app.run()
