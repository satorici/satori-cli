from argparse import ArgumentParser
from math import ceil
from typing import Optional

from satoricli.api import client
from satoricli.cli.utils import autoformat, console

from .base import BaseCommand
from .report import ReportCommand


class ReportsCommand(BaseCommand):
    name = "reports"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)
        parser.add_argument("-f", "--filter")

    def __call__(self, page: int, limit: int, filter: Optional[str], **kwargs):
        res = client.get(
            "/reports", params={"page": page, "limit": limit, "filters": filter}
        ).json()

        if not kwargs["json"]:
            if res["total"] == 0:
                console.print("No reports found")
                return

            ReportCommand.print_report_list(res["rows"])
            console.print(f"Page {page} of {ceil(res['total'] / limit)}")
        else:
            autoformat(res["rows"], jsonfmt=kwargs["json"])
