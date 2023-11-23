import time
from argparse import ArgumentParser
from pathlib import Path
from typing import Literal, Optional

import httpx
from satoricli.api import client

from ..utils import (
    autoformat,
    autotable,
    console,
    error_console,
    print_output,
    print_summary,
    wait,
)
from .base import BaseCommand
from .report import ReportCommand


class RepoCommand(BaseCommand):
    name = "repo"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("repository", metavar="REPOSITORY")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=(
                "show",
                "commits",
                "run",
                "pending",
                "download",
                "tests",
            ),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument("--delete-commits", action="store_true")
        parser.add_argument("-d", "--data", help="Secrets")
        parser.add_argument("-b", "--branch", default="main", help="Repo branch")
        parser.add_argument("--filter", help="Filter names")
        parser.add_argument("-a", "--all", action="store_true")
        parser.add_argument("-l", "--limit", type=int, default=100, help="Limit number")
        parser.add_argument("--fail", action="store_true")
        parser.add_argument("--playbook", help="Satori playbook")
        parser.add_argument(
            "--pending", action="store_true", help="Show pending actions"
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-s", "--sync", action="store_true")
        group.add_argument("-o", "--output", action="store_true")
        group.add_argument("-r", "--report", action="store_true")

    def __call__(
        self,
        repository: str,
        action: Literal[
            "show",
            "commits",
            "run",
            "pending",
            "download",
            "tests",
        ],
        sync: bool,
        output: bool,
        report: bool,
        data: Optional[str],
        filter: Optional[str],
        all: bool,
        limit: int,
        fail: bool,
        playbook: Optional[str],
        pending: bool,
        **kwargs,
    ):
        if action == "tests":
            info = client.get(
                f"/repos/{repository}/tests",
                params={
                    "filter": filter,
                    "all": all,
                    "limit": limit,
                    "fail": fail,
                },
            ).json()
        elif action == "run":
            if playbook and not playbook.startswith("satori://"):
                path = Path(playbook)

                if not path.is_file():
                    error_console.print(f"[error]Playbook {playbook} not found")
                    return 1

                playbook = path.read_text()

            info = client.get(
                "/repos/scan/last",
                params={"url": repository, "data": data or "", "playbook": playbook},
                timeout=300,
            ).json()

            scan_data = info[0]  # TODO: A saner model

            if "error" in scan_data:
                error_console.print(f"[error]{scan_data['error']}")
                return 1

            if sync or output or report:
                report_id = scan_data["status"].split()[-1]
                wait(report_id)

                if sync:
                    print_summary(report_id, kwargs["json"])
                if output:
                    print_output(report_id, kwargs["json"])
                if report:
                    ReportCommand.print_report_asrt(report_id, kwargs["json"])

                return
        elif action in ("download", "pending"):
            info = client.get(f"/repos/{repository}/{action}").json()
        elif action == "show":
            info = client.get(
                f"/repos/{repository}", params={"pending": pending}
            ).json()
        elif action == "commits":
            info = client.get(f"/repos/{repository}/commits").json()
            for row in info:
                row.pop("Parent")
            if kwargs["json"]:
                console.print_json(data=info)
            else:
                autotable(info)
            return

        autoformat(info, jsonfmt=kwargs["json"], list_separator="-" * 48)

    @staticmethod
    def sync_reports_list(report_list: list[dict]):
        completed = []
        n = 0
        with console.status("[bold cyan]Getting results...") as report:
            while len(completed) < len(report_list):
                report = report_list[n]["status"].replace("Report running ", "")
                repo = report_list[n]["repo"]
                if repo not in completed:
                    if report == "Failed to scan commit":
                        console.print(f"[bold]{repo}[/bold] [red]Failed to start")
                        completed.append(repo)

                    try:
                        report_data = client.get(f"/reports/{report}").json()
                    except httpx.HTTPStatusError as e:
                        code = e.response.status_code
                        if code not in (404, 403):
                            console.print(
                                f"[red]Failed to get data\nStatus code: {code}"
                            )
                            return 1

                    else:
                        report_status = report_data.get("status", "Unknown")
                        if report_status in ("Completed", "Undefined"):
                            fails = report_data["fails"]
                            if fails is None:
                                result = "[yellow]Unknown"
                            else:
                                result = (
                                    "[green]Pass"
                                    if fails == 0
                                    else f"[red]Fail({fails})"
                                )
                            console.print(
                                f"[bold]{repo}[/bold] Completed | Result: {result}"
                            )
                            completed.append(repo)
                time.sleep(0.5)
                n += 1
                if n >= len(report_list):
                    n = 0
