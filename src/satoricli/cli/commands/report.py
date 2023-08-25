from argparse import ArgumentParser
from typing import Literal, Optional

import requests
from rich.progress import Progress

from satoricli.api import HOST, client, configure_client
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
                f"{HOST}/reports/{id or ''}",
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
            r = client.get(f"{HOST}/outputs/{id}")
            content = requests.get(r.json()["url"], stream=True, timeout=300)
            format_outputs(content.iter_lines())
        elif action == "files":
            r = client.get(f"{HOST}/reports/{id}/files", stream=True)
            total = int(r.headers["Content-Length"])

            with Progress() as progress:
                task = progress.add_task("Downloading...", total=total)

                with open(f"satorici-files-{id}.tar.gz", "wb") as f:
                    for chunk in r.iter_content():
                        progress.update(task, advance=len(chunk))
                        f.write(chunk)
        elif action == "stop":
            res = client.get(f"{HOST}/reports/{id}/stop").json()
            autoformat(res, jsonfmt=kwargs["json"])
        elif action == "delete":
            client.delete(f"{HOST}/reports/{id}")
            print("Report deleted")
        elif action == "public":
            res = client.patch(f"{HOST}/reports/{id}", json={"public": "invert"}).json()
            autoformat(res)
