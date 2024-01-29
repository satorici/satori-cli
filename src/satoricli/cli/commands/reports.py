from argparse import ArgumentParser
from math import ceil
from typing import Optional

from satoricli.api import client
from satoricli.cli.utils import autotable, console, autoformat

from .base import BaseCommand


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

            autotable(
                [
                    {
                        "id": report["id"],
                        "team": report.get("team"),
                        "playbook_path": report.get("playbook_path"),
                        "playbook_name": report.get("playbook_name"),
                        "execution": report.get("executions"),
                        "status": report.get("status"),
                        "result": report.get("result"),
                        "public": report.get("public"),
                        "execution_time": report.get("execution_time"),
                        "user": report.get("user"),
                        "errors": report.get("errors"),
                        "date": report.get("date"),
                        # "fails": report.get("fails"),
                        # "repo": report.get("repo"),
                        # "branches": report.get("branches"),
                        # "hash": report.get("hash"),
                        # "commit_date": report.get("commit_date"),
                        # "commit_author": report.get("commit_author"),
                        # "commit_email": report.get("commit_email"),
                        # "secrets_count": report.get("secrets_count"),
                        # "playbook_id": report.get("playbook_id"),
                        # "testcases": report.get("testcases"),
                        # "report_url": report.get("report_url"),
                    }
                    for report in res["rows"]
                ],
                widths=(16,)
            )
            console.print(f"Page {page} of {ceil(res['total'] / limit)} | Total: {res['total']}")
        else:
            autoformat(res["rows"], jsonfmt=kwargs["json"])
