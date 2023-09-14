import json
import time
from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Literal, Optional

import httpx
from rich.live import Live
from websocket import WebSocketApp

from satoricli.api import WS_HOST, client, configure_client
from satoricli.cli.models import BootstrapTable
from satoricli.cli.utils import autoformat, autotable, console, group_table
from satoricli.utils import load_config

from ..arguments import date_args
from .base import BaseCommand


class RepoCommand(BaseCommand):
    name = "repo"
    options = (date_args,)

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("repository", metavar="REPOSITORY", nargs="?")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=(
                "show",
                "commits",
                "check-commits",
                "check-forks",
                "scan",
                "scan-stop",
                "scan-status",
                "run",
                "clean",
                "pending",
                "download",
                "tests",
            ),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument(
            "-c", "--coverage", type=float, default=1.0, help="coverage"
        )
        parser.add_argument("--skip-check", action="store_true")
        parser.add_argument("--delete-commits", action="store_true")
        parser.add_argument("-s", "--sync", action="store_true")
        parser.add_argument("-d", "--data", help="Secrets", default="")
        parser.add_argument("-b", "--branch", default="main", help="Repo branch")
        parser.add_argument("--filter", help="Filter names")
        parser.add_argument("-a", "--all", action="store_true")
        parser.add_argument("-l", "--limit", type=int, default=100, help="Limit number")
        parser.add_argument("--fail", action="store_true")
        parser.add_argument("--playbook", help="Playbook", type=Path)

    def __call__(
        self,
        repository: Optional[str],
        action: Literal[
            "show",
            "commits",
            "check-commits",
            "check-forks",
            "scan",
            "scan-stop",
            "scan-status",
            "run",
            "clean",
            "pending",
            "download",
            "tests",
        ],
        coverage: float,
        skip_check: bool,
        delete_commits: bool,
        sync: bool,
        data: Optional[str],
        branch: str,
        filter: Optional[str],
        all: bool,
        limit: int,
        fail: bool,
        from_date: Optional[date],
        to_date: Optional[date],
        playbook: Optional[Path],
        **kwargs,
    ):
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])

        if playbook and not playbook.is_file():
            console.print("Invalid playbook")
            return 1

        if action == "scan":
            info = client.get(
                "/repos/scan",
                params={
                    "url": repository,
                    "data": data,
                    "playbook": playbook and playbook.read_text(),
                    "coverage": coverage,
                    "from": from_date,
                    "to": to_date,
                    "branch": branch,
                },
            ).json()
            if sync:
                return self.scan_sync(repository)
        elif action == "clean":
            info = client.get(
                f"/repos/{repository}/clean", params={"delete_commits": delete_commits}
            ).json()
        elif action == "tests":
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
                params={
                    "url": repository,
                    "data": data,
                    "playbook": playbook and playbook.read_text(),
                },
            ).json()
            if sync:
                if len(info) == 1:
                    console.print(
                        "Report: [link]https://www.satori-ci.com/report_details/?n="
                        + info[0]["status"].replace("Report running ", "")
                    )
                self.sync_reports_list(info)
        elif action == "scan-stop":
            info = client.get(f"/repos/scan/{repository}/stop").json()
        elif action == "scan-status":
            if sync:
                return self.scan_sync(repository)
            else:
                info = client.get(f"/repos/scan/{repository}/status").json()
        elif action == "check-forks":
            info = client.get(f"/repos/scan/{repository}/check-forks").json()
        elif action == "check-commits":
            info = client.get(
                f"/repos/scan/{repository}/check-commits", params={"branch": branch}
            ).json()
            if sync:
                return self.scan_sync(repository)
        elif action in ("commits", "download", "pending"):
            info = client.get(f"/repos/{repository}/{action}").json()
        elif action == "show":
            info = client.get(f"/repos/{repository or ''}").json()

        if not repository and action == "show" and not kwargs["json"]:
            if info["pending"]["rows"]:
                console.rule("[b red]Pending actions", style="red")
                autotable(info["pending"]["rows"], "bold red", widths=(50, 50))
            # Group repos by team name
            group_table(BootstrapTable(**info["list"]), "team", "Private")
            return

        autoformat(info, jsonfmt=kwargs["json"], list_separator="-" * 48)

    def scan_sync(self, id):
        live = Live("Loading data...", console=console, auto_refresh=False)

        def on_open(app: WebSocketApp):
            app.send(json.dumps({"action": "scan-status", "id": id}))

        def on_message(app: WebSocketApp, message):
            print(message)
            try:
                # try to load the message as a json
                stats = json.loads(message)
                # make text readable
                output = autoformat(stats, echo=False)
            except Exception:
                # if fail print plain text
                live.update(message)
            else:
                if output:
                    live.update(output)
            finally:
                live.refresh()

        def on_error(app: WebSocketApp, error):
            console.print("[error]Error:[/] " + str(error))
            app.has_errored = True  # ?????

        def on_close(app: WebSocketApp, close_status_code: int, close_msg: str):
            if close_status_code != 1000:
                on_error(app, close_msg)  # ?????

        app = WebSocketApp(
            WS_HOST,
            on_open=on_open,
            on_message=on_message,
            on_close=on_close,
            on_error=on_error,
            header=client.headers,
        )
        app.run_forever()

        if app.has_errored:
            return 1

    def sync_reports_list(self, report_list: list[dict]) -> None:
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
