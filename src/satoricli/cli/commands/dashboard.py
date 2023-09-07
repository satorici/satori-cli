from argparse import ArgumentParser

from satoricli.api import client, configure_client
from satoricli.cli.utils import autotable, console
from satoricli.utils import load_config

from .base import BaseCommand


class DashboardCommand(BaseCommand):
    name = "dashboard"

    def register_args(self, parser: ArgumentParser):
        pass

    def __call__(self, **kwargs):
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])

        data = client.get("/dashboard")

        if kwargs["json"]:
            console.print_json(data.text)
            return

        info = data.json()

        if info["monitors"]["pending"]:
            console.rule("[b][blue]Monitors[/blue] (Actions required)", style="white")
            autotable(info["monitors"]["pending"], "b blue", widths=(20, 20, None))
        if info["repos"]["pending"]["rows"]:
            console.rule(
                "[b][green]GitHub Repositories[/green] (Actions required)",
                style="white",
            )
            autotable(info["repos"]["pending"]["rows"], "b green", widths=(50, 50))
        if len(info["monitors"]["list"]) == 0:
            console.print("[b]Monitors:[red] no active monitors defined")
        else:
            console.rule("[b blue]Monitors", style="blue")
            autotable(info["monitors"]["list"], "b blue", True)
        if len(info["repos"]["list"]) > 0:
            console.rule("[b green]Github Repositories", style="green")
            autotable(info["repos"]["list"]["rows"], "b green", True)
