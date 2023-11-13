from argparse import ArgumentParser
from typing import Literal

from satoricli.api import client
from satoricli.cli.utils import autoformat
from satoricli.playbooks import display_public_playbooks

from .base import BaseCommand


class PlaybookCommand(BaseCommand):
    name = "playbook"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id", metavar="ID", nargs="?")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=("show", "delete", "public"),
            nargs="?",
            default="show",
            help="action to perform",
        )

    def __call__(self, id: str, action: Literal["show", "delete", "public"], **kwargs):
        if id.startswith("satori://"):
            display_public_playbooks(id)
            return

        list_separator = "-" * 48

        if action == "show":
            data = client.get(f"/playbooks/{id}").json()
            list_separator = None
        elif action == "delete":
            data = client.delete(f"/playbooks/{id}")
            print("Playbook Deleted")
            return
        elif action == "public":
            data = client.patch(f"/playbooks/{id}", json={"public": "invert"}).json()

        autoformat(
            data, jsonfmt=kwargs["json"], list_separator=list_separator, table=True
        )
