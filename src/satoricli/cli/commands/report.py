from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client
from satoricli.cli.utils import autoformat, console, download_files, print_output

from .base import BaseCommand


class ReportCommand(BaseCommand):
    name = "report"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id", metavar="ID", nargs="?")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=("show", "output", "stop", "files", "delete", "public"),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)
        parser.add_argument("-f", "--filter")

    def __call__(
        self,
        id: Optional[str],
        action: Literal["show", "output", "stop", "files", "delete", "public"],
        page: int,
        limit: int,
        filter: Optional[str],
        **kwargs,
    ):
        if action == "show":
            res = client.get(
                f"/reports/{id or ''}",
                params={"page": page, "limit": limit, "filter": filter},
            ).json()

            if not id and not kwargs["json"]:
                if res["count"] == 0:
                    console.print("No reports found")
                    return

                autoformat(res["list"], list_separator="-" * 48)
                console.print(
                    f"[b]Page:[/] {res['current_page']} of {res['total_pages']}"
                )
            else:
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
