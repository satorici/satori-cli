from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, MarkdownViewer, Markdown
from pathlib import Path

from .satori import Satori


class GuiApp(App):
    BINDINGS = [
        ("h", "home", "Home"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
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
            new_info = Markdown2(readme, id="cont")
        self.query_one("#info_c").mount(new_info)
        new_info.scroll_visible()


class Markdown2(MarkdownViewer):
    def _on_markdown_link_clicked(self, message: Markdown.LinkClicked) -> None:
        path = str(Path(__file__).parent)
        path = path + "/../../../docs/" + message.href
        with open(path) as f:
            readme = f.read()
        self.document.update(readme)
