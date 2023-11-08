from argparse import ArgumentParser
from typing import Optional

from satoricli.api import client
from satoricli.cli.utils import autoformat, console

from .base import BaseCommand


class ReportsCommand(BaseCommand):
    name = "reports"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)
        parser.add_argument("-f", "--filter")

    def __call__(
        self,
        page: int,
        limit: int,
        filter: Optional[str],
        **kwargs,
    ):
        res = client.get(
            "/reports", params={"page": page, "limit": limit, "filter": filter}
        ).json()

        if not kwargs["json"]:
            if res["count"] == 0:
                console.print("No reports found")
                return

            autoformat(res["list"], list_separator="-" * 48)
            console.print(f"[b]Page:[/] {res['current_page']} of {res['total_pages']}")
        else:
            autoformat(res, jsonfmt=kwargs["json"])
