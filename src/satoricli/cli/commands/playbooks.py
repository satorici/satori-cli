from argparse import ArgumentParser

from satoricli.api import client
from satoricli.cli.utils import autotable, BootstrapTable, autoformat

from satoricli.playbooks import display_public_playbooks

from .base import BaseCommand
from ..utils import get_offset


class PlaybooksCommand(BaseCommand):
    name = "playbooks"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "-p",
            "--page",
            dest="page",
            type=int,
            default=1,
            help="Playbooks page number",
        )
        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=int,
            default=20,
            help="Page limit number",
        )
        parser.add_argument(
            "--public", action="store_true", help="Fetch public satori playbooks"
        )

    def __call__(self, page: int, limit: int, public: bool, **kwargs):
        if public:
            display_public_playbooks()
            return
        offset = get_offset(page, limit)
        data = client.get(
            "/playbooks", params={"offset": offset, "limit": limit}
        ).json()

        if not kwargs["json"]:
            autotable(BootstrapTable(**data), limit=limit, page=page)
        else:
            autoformat(data["rows"], jsonfmt=kwargs["json"], list_separator="-" * 48)
