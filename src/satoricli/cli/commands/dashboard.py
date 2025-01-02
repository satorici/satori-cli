from argparse import ArgumentParser

from satoricli.api import client
from satoricli.cli.utils import BootstrapTable, autoformat, autotable, console

from .base import BaseCommand
from .reports import ReportsCommand


class DashboardCommand(BaseCommand):
    name = "dashboard"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "--pending", action="store_true", help="Show pending actions"
        )
        parser.add_argument("--public", action="store_true", help="Fetch public")

    def __call__(self, pending: bool, public: bool, **kwargs):
        print_json = kwargs["json"]
        if public:
            self.print_section("/monitors/public", "Monitors", print_json)
            self.print_section("/repos/public", "Repos", print_json)
            self.print_section("/scan/public", "Scans", print_json)
            self.print_section("/reports/public", "Reports", print_json)
        else:
            data = client.get("/dashboard")
            if print_json:
                console.print_json(data.text)
                return
            self.generate_dashboard(data.json(), pending)

    def print_section(self, url: str, title: str, print_json: bool) -> None:
        data = client.get(url).json()
        if not print_json:
            console.rule(title)
            if title == "Reports":
                ReportsCommand.print_table(data["rows"])
                return
            autotable(BootstrapTable(**data))
        else:
            autoformat(data, jsonfmt=True)

    @staticmethod
    def generate_dashboard(info: dict, pending: bool = False):
        if info["monitors"]["pending"]["rows"] and pending:
            console.rule("[b][blue]Monitors[/blue] (Actions required)", style="white")
            autotable(
                info["monitors"]["pending"]["rows"], "b blue", widths=(20, 20, None)
            )
        if info["repos"]["pending"]["rows"] and pending:
            console.rule(
                "[b][green]GitHub Repositories[/green] (Actions required)",
                style="white",
            )
            autotable(info["repos"]["pending"]["rows"], "b green", widths=(50, 50))
        if not info["monitors"]["list"]["rows"]:
            console.print("[b]Monitors:[red] no active monitors defined")
        else:
            console.rule("[b blue]Monitors", style="blue")
            autotable(info["monitors"]["list"]["rows"], "b blue", True)
        if info["repos"]["list"]["rows"]:
            console.rule("[b green]Github Repositories", style="green")
            repos = [
                {**repo, "teams": ",".join(team["name"] for team in repo["teams"])}
                for repo in info["repos"]["list"]["rows"]
            ]
            autotable(repos, "b green", True)
        if info["reports"]["rows"]:
            console.rule("[b red]Last 10 Reports", style="red")
            reports = []
            # Remove unused columns
            for report in info["reports"]["rows"]:
                reports.append(
                    {
                        "id": report["id"],
                        "visibility": report["visibility"],
                        "execution type": report["execution"],
                        "name": report["playbook_name"],
                        "status": report["status"],
                        "result": report["result"],
                        "date": report["date"].replace("T", " "),
                        "team": report["team"],
                    }
                )
            autotable(reports, "b green", widths=(16,))
