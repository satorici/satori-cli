from argparse import ArgumentParser

from satoricli.api import client

from ..utils import (
    BootstrapTable,
    autoformat,
    autotable,
    console,
    group_table,
    get_offset,
)
from .base import BaseCommand


class ReposCommand(BaseCommand):
    name = "repos"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)
        parser.add_argument(
            "--pending", action="store_true", help="Show pending actions"
        )

    def __call__(self, page: int, limit: int, pending:bool, **kwargs):
        offset = get_offset(page, limit)
        repos = client.get("/repos", params={"offset": offset, "limit": limit}).json()

        if not kwargs["json"]:
            # Only get pending repos when is not a json output and on first page
            if page == 1 and pending:
                pending_repos = client.get("/repos/pending").json()
                if pending_repos["rows"]:
                    console.rule("[b red]Pending actions", style="red")
                    autotable(pending_repos["rows"], "bold red", widths=(50, 50))
            # Group repos by team name
            group_table(BootstrapTable(**repos), "team", "Private", page, limit)
        else:
            autoformat(repos, jsonfmt=kwargs["json"], list_separator="-" * 48)
