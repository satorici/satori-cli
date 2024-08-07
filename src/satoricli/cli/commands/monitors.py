from argparse import ArgumentParser

from satoricli.api import client
from satoricli.cli.utils import (
    BootstrapTable,
    autoformat,
    autotable,
    console,
    group_table,
)

from ..utils import get_offset
from .base import BaseCommand


class MonitorsCommand(BaseCommand):
    name = "monitors"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "--deleted", action="store_true", help="Show deleted monitors"
        )
        parser.add_argument(
            "--pending", action="store_true", help="Show pending actions"
        )
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)
        parser.add_argument(
            "--public", action="store_true", help="Fetch public monitors"
        )

    def __call__(
        self,
        deleted: bool,
        pending: bool,
        page: int,
        limit: int,
        public: bool,
        **kwargs,
    ):
        offset = get_offset(page, limit)
        if public:
            monitors = client.get(
                "/monitors/public",
                params={
                    "deleted": deleted,
                    "limit": limit,
                    "offset": offset,
                },
            ).json()
        else:
            monitors = client.get(
                "/monitors", params={"limit": limit, "offset": offset}
            ).json()

        if not kwargs["json"]:
            # Only get pending monitors when is not a json output and on first page
            if page == 1 and pending:
                pending_monitors = client.get("/monitors/pending").json()
                if pending_monitors["rows"]:
                    console.rule("[b red]Pending actions", style="red")
                    autotable(pending_monitors["rows"], "b red", widths=(50, 50))
            console.rule("[b blue]Monitors", style="blue")
            group_table(
                BootstrapTable(**monitors), "team", "Private", page, limit, widths=(16,)
            )
        else:
            autoformat(monitors, jsonfmt=kwargs["json"], list_separator="-" * 48)
