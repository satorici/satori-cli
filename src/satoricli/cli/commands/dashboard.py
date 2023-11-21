from argparse import ArgumentParser

from satoricli.api import client
from satoricli.cli.utils import autotable, console

from .base import BaseCommand


class DashboardCommand(BaseCommand):
    name = "dashboard"

    def register_args(self, parser: ArgumentParser):
        pass

    def __call__(self, **kwargs):
        data = client.get("/dashboard")

        if kwargs["json"]:
            console.print_json(data.text)
            return

        info = data.json()
        self.generate_dashboard(info)

    @staticmethod
    def generate_dashboard(info):
        if info["monitors"]["pending"]["rows"]:
            console.rule("[b][blue]Monitors[/blue] (Actions required)", style="white")
            autotable(
                info["monitors"]["pending"]["rows"], "b blue", widths=(20, 20, None)
            )
        if info["repos"]["pending"]["rows"]:
            console.rule(
                "[b][green]GitHub Repositories[/green] (Actions required)",
                style="white",
            )
            autotable(info["repos"]["pending"]["rows"], "b green", widths=(50, 50))
        if len(info["monitors"]["list"]["rows"]) == 0:
            console.print("[b]Monitors:[red] no active monitors defined")
        else:
            console.rule("[b blue]Monitors", style="blue")
            autotable(info["monitors"]["list"]["rows"], "b blue", True)
        if len(info["repos"]["list"]["rows"]) > 0:
            console.rule("[b green]Github Repositories", style="green")
            autotable(info["repos"]["list"]["rows"], "b green", True)
        if len(info["reports"]["list"]) > 0:
            console.rule("[b red]Last 10 Reports", style="red")
            reports = []
            # Remove unused columns
            for report in info["reports"]["list"]:
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
            autotable(reports, "b green")
