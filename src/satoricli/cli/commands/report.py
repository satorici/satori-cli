from argparse import ArgumentParser
from typing import Literal

from satoricli.api import client
from satoricli.cli.utils import autoformat, download_files, print_output

from .base import BaseCommand


class ReportCommand(BaseCommand):
    name = "report"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id", metavar="ID")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=("show", "output", "stop", "files", "delete", "public"),
            nargs="?",
            default="show",
            help="action to perform",
        )

    def __call__(
        self,
        id: str,
        action: Literal["show", "output", "stop", "files", "delete", "public"],
        **kwargs,
    ):
        if action == "show":
            res = client.get(f"/reports/{id}").json()
            autoformat(res, jsonfmt=kwargs["json"])
        elif action == "output":
            print_output(id, print_json=kwargs["json"])
        elif action == "files":
            download_files(id)
        elif action == "stop":
            res = client.get(f"/reports/{id}/stop").json()
            autoformat(res, jsonfmt=kwargs["json"])
        elif action == "delete":
            client.delete(f"/reports/{id}")
            print("Report deleted")
        elif action == "public":
            res = client.patch(f"/reports/{id}", json={"public": "invert"}).json()
            autoformat(res)
