from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client, configure_client
from satoricli.cli.utils import autoformat
from satoricli.playbooks import display_public_playbooks
from satoricli.utils import load_config

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
        parser.add_argument("-d", "--delete", action="store_true")
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

    def __call__(
        self,
        id: Optional[str],
        action: Literal["show", "delete", "public"],
        page: int,
        limit: int,
        public: bool,
        **kwargs,
    ):
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])
        list_separator = "-" * 48

        if public or (id and id.startswith("satori://")):
            display_public_playbooks(id)
            return

        if action == "show":
            if not id:
                data = client.get(
                    "/playbooks", params={"limit": limit, "page": page}
                ).json()
            else:
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
