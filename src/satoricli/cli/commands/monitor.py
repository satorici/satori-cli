from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client, configure_client
from satoricli.cli.utils import (
    autoformat,
    autotable,
    console,
    BootstrapTable,
    group_table,
)
from satoricli.utils import load_config

from .base import BaseCommand


class MonitorCommand(BaseCommand):
    name = "monitor"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id", metavar="ID", nargs="?")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=("show", "start", "stop", "delete", "public", "clean"),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument(
            "--clean", action="store_true", help="clean all report related"
        )
        parser.add_argument(
            "--deleted", action="store_true", help="show deleted monitors"
        )

    def __call__(
        self,
        id: Optional[str],
        action: Literal["show", "start", "stop", "delete", "public", "clean"],
        clean: bool,
        deleted: bool,
        **kwargs,
    ):
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])

        if action == "delete":
            client.delete(f"/monitors/{id}", params={"clean": clean})
            print("Monitor deleted")
            return
        elif action == "show":
            info = client.get(
                f"/monitors/{id or ''}", params={"deleted": deleted}
            ).json()
            if id and not kwargs["json"]:
                reports = info.pop("reports")
                autoformat(info)
                autotable(reports)
                return
        elif action == "public":
            info = client.patch(f"/monitors/{id}", json={"public": "invert"}).json()
        elif action in ("start", "stop"):
            info = client.patch(f"/monitors/{id}/{action}").json()
        elif action == "clean":
            client.delete(f"/monitors/{id}/reports")
            print("Monitor reports cleaned")
            return

        if not id and action == "show" and not kwargs["json"]:
            if len(info["pending"]["rows"]) > 1:
                console.rule("[b red]Pending actions", style="red")
                autotable(info["pending"]["rows"], "b red")
            console.rule("[b blue]Monitors", style="blue")
            group_table(BootstrapTable(**info["list"]), "team", "Private")
            return

        autoformat(info, jsonfmt=kwargs["json"], list_separator="*" * 48)
