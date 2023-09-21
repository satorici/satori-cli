import time
from argparse import ArgumentParser
from typing import Literal, Optional

import httpx

from satoricli.api import client, configure_client
from satoricli.utils import load_config

from ..utils import BootstrapTable, autoformat, autotable, console, group_table
from .base import BaseCommand
from .scan import ScanCommand


class RepoCommand(BaseCommand):
    name = "repo"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("repository", metavar="REPOSITORY", nargs="?")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=(
                "show",
                "commits",
                "check-commits",
                "run",
                "check-forks",
                "pending",
                "download",
                "tests",
            ),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument("--delete-commits", action="store_true")
        parser.add_argument("-s", "--sync", action="store_true")
        parser.add_argument("-d", "--data", help="Secrets")
        parser.add_argument("-b", "--branch", default="main", help="Repo branch")
        parser.add_argument("--filter", help="Filter names")
        parser.add_argument("-a", "--all", action="store_true")
        parser.add_argument("-l", "--limit", type=int, default=100, help="Limit number")
        parser.add_argument("--fail", action="store_true")
        parser.add_argument("--playbook", help="Satori playbook")

    def __call__(
        self,
        repository: Optional[str],
        action: Literal[
            "show",
            "commits",
            "check-commits",
            "check-forks",
            "run",
            "pending",
            "download",
            "tests",
        ],
        sync: bool,
        data: Optional[str],
        branch: str,
        filter: Optional[str],
        all: bool,
        limit: int,
        fail: bool,
        playbook: Optional[str],
        **kwargs,
    ):
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])

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
            info = client.get(
                "/repos/scan/last",
                params={"url": repository, "data": data or "", "playbook": playbook},
                timeout=300,
            ).json()
            if sync:
                if len(info) == 1:
                    console.print(
                        "Report: [link]https://www.satori-ci.com/report_details/?n="
                        + info[0]["status"].replace("Report running ", "")
                    )
                return self.sync_reports_list(info)
        elif action == "check-forks":
            info = client.get(f"/repos/scan/{repository}/check-forks").json()
        elif action == "check-commits":
            console.print(f"Checking the list of commits of the repo {repository}")
            info = client.get(
                f"/repos/scan/{repository}/check-commits", params={"branch": branch}
            ).json()
            if sync:
                return ScanCommand.scan_sync(repository)
        elif action in ("download", "pending"):
            info = client.get(f"/repos/{repository}/{action}").json()
        elif action == "show":
            info = client.get(f"/repos/{repository or ''}").json()
        elif action == "commits":
            info = client.get(f"/repos/{repository}/commits").json()
            for row in info:
                row.pop("Parent")
                row.pop("Errors")
            if kwargs["json"]:
                console.print_json(data=info)
            else:
                autotable(info)
            return

        if not repository and action == "show" and not kwargs["json"]:
            if info["pending"]["rows"]:
                console.rule("[b red]Pending actions", style="red")
                autotable(info["pending"]["rows"], "bold red", widths=(50, 50))
            # Group repos by team name
            group_table(BootstrapTable(**info["list"]), "team", "Private")
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
