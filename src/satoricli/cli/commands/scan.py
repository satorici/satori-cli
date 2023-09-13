import json
from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from rich.live import Live
from websocket import WebSocketApp

from satoricli.api import WS_HOST, client, configure_client
from satoricli.cli.utils import autoformat, console
from satoricli.utils import load_config

from ..arguments import date_args
from .base import BaseCommand


class ScanCommand(BaseCommand):
    name = "scan"
    options = (date_args,)

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("repository", metavar="REPOSITORY", nargs="?")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=(
                "new",
                "stop",
                "status",
                "clean",
            ),
            nargs="?",
            default="new",
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
        parser.add_argument("--playbook", help="Playbook", type=Path)

    def __call__(
        self,
        repository: Optional[str],
        action: Literal[
            "new",
            "stop",
            "status",
            "clean",
        ],
        coverage: float,
        sync: bool,
        delete_commits: bool,
        data: Optional[str],
        branch: str,
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

        if action == "new" and repository:
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
        elif action == "new" and not repository:
            return
        elif action == "clean":
            info = client.get(
                f"/repos/{repository}/clean", params={"delete_commits": delete_commits}
            ).json()
        elif action == "stop":
            info = client.get(f"/repos/scan/{repository}/stop").json()
        elif action == "status":
            if sync:
                return self.scan_sync(repository)
            else:
                info = client.get(f"/repos/scan/{repository}/status").json()

        if kwargs["json"]:
            console.print_json(data=info)
        else:
            autoformat(info)

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
