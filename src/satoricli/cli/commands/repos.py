from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client

from ..utils import (
    BootstrapTable,
    autoformat,
    autotable,
    console,
    error_console,
    get_offset,
    group_table,
)
from .base import BaseCommand


class ReposCommand(BaseCommand):
    name = "repos"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=("show", "playbook"),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument(
            "action2", choices=("list", "add", "del"), nargs="?", default="list"
        )
        parser.add_argument("playbook_uri", default=None, nargs="?")
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)
        parser.add_argument(
            "--pending", action="store_true", help="Show pending actions"
        )
        parser.add_argument("--public", action="store_true", help="Fetch public repos")

    def __call__(
        self,
        action: Literal["show", "playbook"],
        action2: Literal["list", "add", "del"],
        playbook_uri: Optional[str],
        page: int,
        limit: int,
        pending: bool,
        public: bool,
        **kwargs,
    ):
        offset = get_offset(page, limit)
        if action == "show":
            url = "/repos/public" if public else "/repos"
            repos = client.get(url, params={"offset": offset, "limit": limit}).json()

            if not kwargs["json"]:
                # Only get pending repos when is not a json output and on first page
                if page == 1 and pending:
                    pending_repos = client.get("/repos/pending").json()
                    if pending_repos["rows"]:
                        console.rule("[b red]Pending actions", style="red")
                        autotable(pending_repos["rows"], "bold red", widths=(50, 50))
                if public:
                    autotable(BootstrapTable(**repos), page=page, limit=limit)
                else:
                    # Group repos by team name
                    group_table(
                        BootstrapTable(**repos), "teams", "Private", page, limit
                    )
            else:
                autoformat(repos, jsonfmt=kwargs["json"], list_separator="-" * 48)
        else:  # playbook
            if action2 == "list":
                data = client.get(
                    "/repos/playbooks", params={"offset": offset, "limit": limit}
                ).json()
                autotable(data["rows"], page=page, limit=limit)
                return
            elif action2 == "add":
                if not playbook_uri:
                    error_console.print("Please insert a playbook name")
                    raise
                data = client.post(
                    "/repos/playbooks", params={"playbook": playbook_uri}
                ).json()
            elif action2 == "del":
                client.delete("/repos/playbooks", params={"playbook": playbook_uri})
                data = {"message": "Global playbook deleted"}
            autoformat(data, jsonfmt=kwargs["json"])
