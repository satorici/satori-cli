from argparse import ArgumentParser
from typing import Literal, Optional

import httpx
from rich.progress import Progress

from satoricli.api import client, configure_client
from satoricli.cli.utils import autoformat, console, format_outputs
from satoricli.utils import load_config

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
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])

        if action == "show":
            res = client.get(
                f"/reports/{id or ''}",
                params={"page": page, "limit": limit, "filter": filter},
            ).json()

            if not id and not kwargs["json"]:
                autoformat(res["list"], list_separator="-" * 48)
                console.print(
                    f"[b]Page:[/] {res['current_page']} of {res['total_pages']}"
                )
            else:
                autoformat(res, jsonfmt=kwargs["json"])
        elif action == "output":
            r = client.get(f"/outputs/{id}")
            with httpx.stream("GET", r.json()["url"], timeout=300) as s:
                format_outputs(s.iter_lines())
        elif action == "files":
            r = client.get(f"/outputs/{id}/files")
            with httpx.stream("GET", r.json()["url"], timeout=300) as s:
                total = int(s.headers["Content-Length"])

                with Progress() as progress:
                    task = progress.add_task("Downloading...", total=total)

                    with open(f"satorici-files-{id}.tar.gz", "wb") as f:
                        for chunk in s.iter_raw():
                            progress.update(task, advance=len(chunk))
                            f.write(chunk)
        elif action == "stop":
            res = client.get(f"/reports/{id}/stop").json()
            autoformat(res, jsonfmt=kwargs["json"])
        elif action == "delete":
            client.delete(f"/reports/{id}")
            print("Report deleted")
        elif action == "public":
            res = client.patch(f"/reports/{id}", json={"public": "invert"}).json()
            autoformat(res)
