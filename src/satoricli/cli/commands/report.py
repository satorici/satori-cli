from argparse import ArgumentParser
import re
from typing import Literal, Optional
from rich.table import Table

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

                ReportCommand.gen_report_table(res["list"])
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

    @staticmethod
    def gen_report_table(list):
        print("Available size:", console.size.width - 4)
        for report in list:
            table = Table(
                show_header=False, show_lines=True, highlight=True, expand=True
            )
            ReportCommand.add_row(
                [
                    ["ID", report["id"]],
                    ["Team", report["team"]],
                    ["Playbook name", report["playbook_name"]],
                ],
                table,
            )
            ReportCommand.add_row(
                [
                    ["Execution type", report["execution"]],
                    ["Public", report["public"]],
                    ["Time required", report["time required"]],
                    ["User", report["user"]],
                    ["Date", report["date"].replace("T"," ")],
                    ["Status", report["status"]],
                    ["Result", report["result"]],
                ],
                table,
            )

            if report.get("repo"):
                ReportCommand.add_row(
                    [
                        ["Repo", report["repo"]],
                        ["Branch", report["branches"]],
                        ["Hash", report["hash"]],
                        ["Commit author", report["commit_author"]],
                    ],
                    table,
                )
            ReportCommand.add_row(
                [
                    ["Playbook", report["playbook_id"]],
                    ["Url", report["playbook_url"]],
                ],
                table,
            )
            if report["testcases"]:
                tests = ""
                for test in report["testcases"]:
                    style = "[pass]" if re.search(r"pass$", test) else "[fail]"
                    tests += f"\n  ○ {style}{test}"
                table.add_row(f"[b]Testcases:[/]{tests}")
            console.print(table)

    @staticmethod
    def add_row(row_content: list, table: Table):
        available_size = console.width - 4
        row_text = ""
        n = 0
        for content in row_content:
            n += 1
            text = f"[b]{content[0]}:[/] {content[1]}"
            if n < len(row_content):  # avoid to add separators to the last column
                text += " | "
            if len(text) - 6 > available_size:
                text = "\n" + text
                available_size = console.width - 4
            available_size -= len(text) - 6  # 6: dont include non-visible chars [b][/]
            row_text += text
        table.add_row(row_text)
