from argparse import ArgumentParser

from satoricli.api import client
from satoricli.cli.utils import (
    BootstrapTable,
    autoformat,
    autotable,
    console,
    group_table,
)

from .base import BaseCommand


class MonitorsCommand(BaseCommand):
    name = "monitors"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "--deleted", action="store_true", help="show deleted monitors"
        )
        parser.add_argument(
            "--pending", action="store_true", help="show pending actions"
        )

    def __call__(self, deleted: bool, pending: bool, **kwargs):
        info = client.get(
            "/monitors", params={"deleted": deleted, "pending": pending}
        ).json()

        if not kwargs["json"]:
            if len(info["pending"]["rows"]) > 1:
                console.rule("[b red]Pending actions", style="red")
                autotable(info["pending"]["rows"], "b red")
            console.rule("[b blue]Monitors", style="blue")
            group_table(BootstrapTable(**info["list"]), "team", "Private")
        else:
            autoformat(info, jsonfmt=kwargs["json"], list_separator="*" * 48)
