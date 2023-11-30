from argparse import ArgumentParser
from math import ceil

from satoricli.api import client
from satoricli.cli.utils import autoformat, console
from satoricli.playbooks import display_public_playbooks

from .base import BaseCommand


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

        data = client.get("/playbooks", params={"limit": limit, "page": page}).json()

        autoformat(
            data["items"], jsonfmt=kwargs["json"], list_separator="-" * 48, table=True
        )
        console.print(f"Page {page} of {ceil(data['total'] / limit)}")
