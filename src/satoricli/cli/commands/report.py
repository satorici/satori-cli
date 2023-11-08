from argparse import ArgumentParser
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

                autoformat(res["list"], list_separator="-" * 48)
                self.gen_report_table(res["list"])
                # console.print(
                #     f"[b]Page:[/] {res['current_page']} of {res['total_pages']}"
                # )
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

    def gen_report_table(self, list):
        for report in list:
            table = Table(show_header=False, show_lines=True, highlight=True)
            table.add_row(
                f"[b]ID:[/] {report['id']} | [b]Public:[/] {report['public']}"
                + f" | [b]Execution type:[/] {report['execution']}"
                + f" | [b]Time required:[/] {report['time required']}"
                + f" | [b]Result:[/] {report['result']} | [b]User:[/] {report['user']}"
                + f" | [b]Status:[/] {report['status']} | [b]Team:[/] {report['team']}"
                + f" | [b]Date:[/] {report['result']}"
            )
            if report.get("repo"):
                table.add_row(
                    f"[b]Repo:[/] {report['repo']} | [b]Branch:[/] {report['branches']}"
                    + f" | [b]Hash:[/] {report['hash']}"
                    + f" | [b]Commit author:[/] {report['commit_author']}"
                )
            table.add_row(
                f"[b]Playbook:[/] {report['playbook_id']}"
                + f" | [b]Name:[/] {report['playbook_name']}"
                + f" | [b]Url:[/] {report['playbook_url']}"
            )
            if report['testcases']:
                testcases = '\n  ○ '.join(report['testcases'])
                table.add_row(f"[b]Testcases:[/]\n  ○ {testcases}")
            console.print(table)
