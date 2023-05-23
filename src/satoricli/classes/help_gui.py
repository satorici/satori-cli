from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, MarkdownViewer
from pathlib import Path

from .satori import Satori


class GuiApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("h", "home", "Home"),
    ]
    TITLE = "Satori CLI"

    def __init__(self, satori: Satori, **kargs):
        self.satori = satori
        super().__init__(**kargs)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Footer()
        yield VerticalScroll(VerticalScroll(id="cont"), id="info_c")

    def on_mount(self) -> None:
        self.action_home()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_home(self) -> None:
        info = self.query_one("#cont")
        info.remove()
        path = str(Path(__file__).parent)
        with open(path + "/../../../docs/README.md") as f:
            readme = f.read()
            new_info = MarkdownViewer(readme, id="cont", show_table_of_contents=True)
        self.query_one("#info_c").mount(new_info)
        new_info.scroll_visible()
