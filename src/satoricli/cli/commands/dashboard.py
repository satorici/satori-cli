from argparse import ArgumentParser

from satoricli.api import client
from satoricli.cli.utils import autotable, console

from .base import BaseCommand


class DashboardCommand(BaseCommand):
    name = "dashboard"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "--pending", action="store_true", help="Show pending actions"
        )

    def __call__(self, pending: bool, **kwargs):
        data = client.get("/dashboard")

        if kwargs["json"]:
            console.print_json(data.text)
            return

        info = data.json()
        self.generate_dashboard(info, pending)

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
            autotable(info["repos"]["list"]["rows"], "b green", True)
        if info["reports"]["rows"]:
            console.rule("[b red]Last 10 Reports", style="red")
            reports = []
            # Remove unused columns
            for report in info["reports"]["rows"]:
                reports.append(
                    {
                        "id": report["id"],
                        "public": report["public"],
                        "execution type": report["execution"],
                        "name": report["playbook_name"],
                        "status": report["status"],
                        "result": report["result"],
                        "date": report["date"].replace("T", " "),
                        "team": report["team"],
                    }
                )
            autotable(reports, "b green", widths=(16,))
