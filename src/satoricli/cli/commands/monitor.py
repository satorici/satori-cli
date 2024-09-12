from argparse import ArgumentParser
from typing import Literal

from satoricli.api import client
from satoricli.cli.utils import (
    BootstrapTable,
    autoformat,
    autotable,
    remove_keys_list_dict,
)

from .base import BaseCommand


class MonitorCommand(BaseCommand):
    name = "monitor"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id", metavar="ID")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=("show", "start", "stop", "delete", "public", "clean"),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument(
            "--clean", action="store_true", help="clean all report related"
        )
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)

    def __call__(
        self,
        id: str,
        action: Literal["show", "start", "stop", "delete", "public", "clean"],
        clean: bool,
        page: int,
        limit: int,
        **kwargs,
    ):
        if action == "delete":
            client.delete(f"/monitors/{id}", params={"clean": clean})
            print("Monitor deleted")
            return
        elif action == "show":
            info = client.get(
                f"/monitors/{id}", params={"page": page, "limit": limit}
            ).json()
            if not kwargs["json"]:
                reports: dict = info.pop("reports")
                reports["rows"] = remove_keys_list_dict(reports["rows"], ("fails",))
                autoformat(info)
                autotable(BootstrapTable(**reports), page=page, limit=limit)
                return
        elif action == "public":
            info = client.patch(f"/monitors/{id}", json={"public": "invert"}).json()
        elif action in ("start", "stop"):
            client.patch(f"/monitors/{id}/{action}")
            print(f"Monitor {'stopped' if action == 'stop' else 'started'}")
            return
        elif action == "clean":
            client.delete(f"/monitors/{id}/reports")
            print("Monitor reports cleaned")
            return

        autoformat(info, jsonfmt=kwargs["json"], list_separator="*" * 48)
