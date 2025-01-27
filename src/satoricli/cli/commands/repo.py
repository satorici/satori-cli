import time
from argparse import ArgumentParser
from pathlib import Path
from typing import Literal, Optional

import httpx

from satoricli.api import client

from ..utils import (
    BootstrapTable,
    autoformat,
    autotable,
    console,
    error_console,
    execution_time,
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
                "tests",
                "playbook",
                "visibility",
                "params",
            ),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument(
            "action2",
            choices=("list", "add", "del", "public", "private", "unlisted"),
            nargs="?",
            default="list",
        )
        parser.add_argument("playbook_uri", nargs="?", default=None)
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
        parser.add_argument("-s", "--sync", action="store_true")
        parser.add_argument("-o", "--output", action="store_true")
        parser.add_argument("-r", "--report", action="store_true")
        parser.add_argument(
            "--visibility", choices=("public", "private", "unlisted"), default="private"
        )

    def __call__(
        self,
        repository: str,
        action: Literal[
            "show",
            "commits",
            "run",
            "pending",
            "tests",
            "playbook",
            "params",
            "visibility",
        ],
        action2: Literal["list", "add", "del", "Public", "Private", "Unlisted"],
        playbook_uri: Optional[str],
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
        visibility: Literal["public", "private", "unlisted"],
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

            info = client.post(
                "/scan/last",
                json={
                    "url": repository,
                    "data": data or "",
                    "playbook": playbook,
                    "visibility": visibility.capitalize(),
                },
                timeout=300,
            ).json()

            self.repo_run(info, sync, output, report, kwargs)

            return
        elif action == "pending":
            info = client.get(f"/repos/{repository}/pending").json()
        elif action == "show":
            reports = client.get(
                "/reports",
                params={"filters": f"repo={repository},ignore=scan"},
            ).json()
            try:
                info = client.get(
                    f"/repos/{repository}", params={"pending": pending}
                ).json()
            except Exception:
                if reports["rows"]:
                    info = {}
                else:
                    raise

            if kwargs["json"]:
                info["reports"] = reports
                console.print_json(data=info)
            else:
                playbooks = info.get("playbooks", {})
                info["playbooks"] = ""
                autoformat(info)
                autotable(playbooks.get("rows", []))
                console.print("Reports:")
                reports_cols = [
                    {
                        "ID": report["id"],
                        "Commit hash": (
                            report["hash"][:7] if report["hash"] else report["hash"]
                        ),
                        "Commit author": report["commit_author"],
                        "Execution time": execution_time(report["execution_time"]),
                        "Result": report["result"],
                        "Status": report["status"],
                        "User": report["user"],
                        "Date": report["date"],
                    }
                    for report in reports["rows"]
                ]
                autotable(reports_cols)
            return
        elif action == "commits":
            info = client.get(f"/repos/{repository}/commits").json()
            for row in info:
                row.pop("parent", None)
            if kwargs["json"]:
                console.print_json(data=info)
            else:
                autotable(info)
            return
        elif action == "playbook":
            if action2 == "list":
                info = client.get(f"/repos/{repository}/playbooks").json()
                if not kwargs["json"]:
                    autotable(BootstrapTable(**info))
                    return
            elif action2 == "add":
                if not playbook_uri:
                    error_console.print("Please insert a playbook name")
                    raise
                info = client.post(
                    f"/repos/{repository}/playbooks", params={"playbook": playbook_uri}
                ).json()
            elif action2 == "del":
                client.delete(
                    f"/repos/{repository}/playbooks", params={"playbook": playbook_uri}
                )
                info = {"message": "Repo playbook deleted"}
        elif action == "visibility":
            info = client.patch(
                f"/repos/{repository}", json={"visibility": action2.capitalize()}
            ).json()
        elif action == "params":
            if action2 == "list":
                info = client.get(f"/repos/{repository}/secrets").json()
                if not kwargs["json"]:
                    autotable(BootstrapTable(**info), numerate=True)
                    return
            elif action2 == "add":
                info = client.post(
                    f"/repos/{repository}/secrets", params={"secret": playbook_uri}
                ).json()
            elif action2 == "del":
                client.delete(
                    f"/repos/{repository}/secrets", params={"key": playbook_uri}
                )
                info = {"message": f"Secret {playbook_uri} deleted"}
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

    def repo_run(
        self, scan_data: dict, sync: bool, output: bool, report: bool, kwargs: dict
    ):
        autoformat(scan_data, jsonfmt=kwargs["json"])

        if any((sync, output, report)) and scan_data["status"] == "Running":
            reports_list = []
            while not reports_list:
                res = client.get(f"/scan/{scan_data['id']}/reports").json()
                reports_list = res.get("rows")
                time.sleep(1)
            report_id = reports_list[0]["id"]
            wait(report_id)
            if sync:
                print_summary(report_id, kwargs["json"])
            if output:
                print_output(report_id, kwargs["json"])
            if report:
                ReportCommand.print_report_asrt(report_id, kwargs["json"])
