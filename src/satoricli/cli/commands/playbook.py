from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client
from satoricli.cli.utils import VISIBILITY_VALUES, autoformat, error_console
from satoricli.playbooks import display_public_playbooks

from .base import BaseCommand


class PlaybookCommand(BaseCommand):
    name = "playbook"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id", metavar="ID")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=(
                "show",
                # "delete",
                "visibility",
            ),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument("action2", nargs="?", default=None)
        parser.add_argument(
            "--original",
            action="store_true",
            help="Display playbook without formatting",
        )

    def __call__(
        self,
        id: str,
        action: Literal[
            "show",
            # "delete",
            "visibility",
        ],
        action2: Optional[str],
        original: bool,
        **kwargs,
    ):
        if id.startswith("satori://"):
            display_public_playbooks(id, original)
            return

        list_separator = "-" * 48

        if action == "show":
            data = client.get(f"/playbooks/{id}").json()
            list_separator = None
        # elif action == "delete":
        #     data = client.delete(f"/playbooks/{id}")
        #     print("Playbook Deleted")
        #     return
        elif action == "visibility":
            if not action2 or action2 not in VISIBILITY_VALUES:
                error_console.print(
                    f"Allowed values for visibility: {VISIBILITY_VALUES}"
                )
                return 1
            data = client.patch(
                f"/playbooks/{id}", json={"visibility": action2.capitalize()}
            ).json()

        autoformat(
            data, jsonfmt=kwargs["json"], list_separator=list_separator, table=True
        )
