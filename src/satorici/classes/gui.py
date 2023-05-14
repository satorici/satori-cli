from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Static, DataTable, Markdown
from satorici.classes.satori import Satori
from pathlib import Path


class GuiApp(App):
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]
    TITLE = "Satori CLI"

    def __init__(self, satori: Satori, **kargs):
        self.satori = satori
        super().__init__(**kargs)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Footer()
        yield Horizontal(
            Button("Readme", id="readme"),
            Button("Repos", id="repo", variant="primary"),
            Button("Reports", id="report", variant="success"),
            Button("Monitors", id="monitor", variant="error"),
            id="menu",
        )
        yield VerticalScroll(Info(id="cont"), id="info_c")

    def on_mount(self) -> None:
        menu = self.query_one("#menu")
        menu.styles.layout = "horizontal"
        menu.styles.height = 3
        menu.styles.width = "100%"
        menu.styles.align_horizontal = "center"

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def on_button_pressed(self, event: Button.Pressed) -> None:
        info = self.query_one("#cont")
        info.remove()
        if event.button.id == "readme":
            path = str(Path(__file__).parent)
            with open(path + "/../../../README.md") as f:
                readme = f.read()
                new_info = Markdown(readme, id="cont")
            self.query_one("#info_c").mount(new_info)
            new_info.scroll_visible()
            return None
        new_info = Info(id="cont")
        if event.button.id == "report":
            res = self.satori.api.reports("GET", "", "")
            headers = ("Date", "Author", "Email", "Status", "Report")
            rows = map(
                lambda x: [
                    x["Date"],
                    x["Author"],
                    x["Email"],
                    x["Status"],
                    x["Report"],
                ],
                res,
            )
            new_info.data = {"headers": headers, "rows": rows}
        elif event.button.id == "monitor":
            res = self.satori.api.monitors("GET", "", "")
            headers = ("ID", "Name", "Status", "Last Result", "Schedule", "Errors")
            rows = map(
                lambda x: [
                    x["id"],
                    x["name"],
                    x["status"],
                    x["last result"],
                    x["schedule"],
                    x["errors"],
                ],
                res["list"],
            )
            new_info.data = {"headers": headers, "rows": rows}
        elif event.button.id == "repo":
            res = self.satori.api.repos("GET", "", "")
            headers = ("Repo", "CI", "Playbook", "Result", "Errors")
            rows = map(
                lambda x: [
                    x["repo"],
                    x["ci"],
                    x["playbook"],
                    x["result"],
                    x["errors"],
                ],
                res["list"],
            )
            new_info.data = {"headers": headers, "rows": rows}
        self.query_one("#info_c").mount(new_info)
        new_info.scroll_visible()


class Info(Static):
    data = {"headers": [], "rows": []}

    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.zebra_stripes = True
        table.add_columns(*self.data["headers"])
        table.add_rows(self.data["rows"])
