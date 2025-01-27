import json
import re
from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from rich.live import Live
from websocket import WebSocketApp

from satoricli.api import WS_HOST, client
from satoricli.cli.utils import (
    VISIBILITY_VALUES,
    BootstrapTable,
    autoformat,
    autotable,
    console,
    error_console,
    execution_time,
    remove_keys_list_dict,
)

from ..arguments import date_args
from .base import BaseCommand

SCANID_REGEX = re.compile(r"s\w{15}")


class ScanCommand(BaseCommand):
    name = "scan"
    options = (date_args,)

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("repository", metavar="REPOSITORY")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=(
                "new",
                "stop",
                "status",
                "reports",
                "clean",
                "check-forks",
                "check-commits",
                "visibility",
                "delete",
            ),
            nargs="?",
            default="new",
            help="action to perform",
        )
        parser.add_argument("action2", nargs="?", default=None)
        parser.add_argument(
            "-c", "--coverage", type=float, default=1.0, help="coverage"
        )
        parser.add_argument("--skip-check", action="store_true")
        parser.add_argument("--delete-commits", action="store_true")
        parser.add_argument("-s", "--sync", action="store_true")
        parser.add_argument("-d", "--data", help="Secrets", default="")
        parser.add_argument("-b", "--branch", default="main", help="Repo branch")
        parser.add_argument("--filter", help="Filter names")
        parser.add_argument("--playbook", help="Playbook url or file")
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)

    def __call__(
        self,
        repository: str,
        action: Literal[
            "new",
            "stop",
            "status",
            "reports",
            "clean",
            "check-forks",
            "check-commits",
            "visibility",
            "delete",
        ],
        action2: Optional[str],
        coverage: float,
        sync: bool,
        delete_commits: bool,
        data: Optional[str],
        branch: str,
        from_date: Optional[date],
        to_date: Optional[date],
        playbook: Optional[str],
        page: int,
        limit: int,
        team: str,
        **kwargs,
    ):
        if SCANID_REGEX.match(repository) and action == "new":
            # show scan status instead of trying to create a new scan if is a scan id
            action = "status"

        if action == "new":
            config = None

            if playbook:
                if (path := Path(playbook)) and path.is_file():
                    config = path.read_text()

                if playbook.startswith("satori://"):
                    config = playbook

            info = client.post(
                "/scan",
                json={
                    "url": repository,
                    "data": data,
                    "playbook": config,
                    "coverage": coverage,
                    "from": from_date,
                    "to": to_date,
                    "branch": branch,
                    "team": team,
                },
            ).json()
            if sync:
                return self.scan_sync(repository)
        elif action == "clean":
            client.delete(
                f"scan/{repository}/reports", params={"delete_commits": delete_commits}
            )
            info = {"message": "Scan reports cleaned"}
        elif action == "delete":
            client.delete(f"scan/{repository}")
            info = {"message": "Scan deleted"}
        elif action == "stop":
            self.check_scan_id(repository)
            info = client.get(f"/scan/stop/{repository}").json()
        elif action == "status":
            self.check_scan_id(repository)
            if sync:
                return self.scan_sync(repository)
            else:
                info = client.get(f"/scan/status/{repository}").json()
        elif action == "reports":
            self.check_scan_id(repository)
            info = client.get(
                f"/scan/{repository}/reports", params={"limit": limit, "page": page}
            ).json()
            if not kwargs["json"]:
                info["rows"] = remove_keys_list_dict(info["rows"], ("fails", "created"))
                info["rows"] = [
                    {**x, "execution_time": execution_time(x["execution_time"])}
                    for x in info["rows"]
                ]
                autotable(BootstrapTable(**info), page=page, limit=limit)
                return
        elif action == "check-forks":
            info = client.get(f"/scan/{repository}/check-forks").json()
        elif action == "check-commits":
            console.print(f"Checking the list of commits of the repo {repository}")
            info = client.post(
                "/scan/check-commits", json={"repo": repository, "branch": branch}
            ).json()
            if sync:
                return ScanCommand.scan_sync(repository)
        elif action == "visibility":
            if not action2 or action2 not in VISIBILITY_VALUES:
                error_console.print(
                    f"Allowed values for visibility: {VISIBILITY_VALUES}"
                )
                return 1
            info = client.patch(
                f"/scan/{repository}", json={"visibility": action2.capitalize()}
            ).json()
        autoformat(info, jsonfmt=kwargs["json"], list_separator="-" * 48)

    @staticmethod
    def scan_sync(id):
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
            header={"Authorization": client.headers["Authorization"]},
        )
        app.run_forever()

        if app.has_errored:
            return 1

    def check_scan_id(self, scan_id: str) -> None:
        if not SCANID_REGEX.match(scan_id):
            raise Exception("Please enter a scan ID")

    def check_repo_id(self, repo_id: str) -> None:
        if not re.match(r"[^/]+/[^/]+", repo_id):
            raise Exception("Please enter a repo ID")
