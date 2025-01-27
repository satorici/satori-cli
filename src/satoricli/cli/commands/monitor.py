from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client
from satoricli.cli.utils import (
    VISIBILITY_VALUES,
    BootstrapTable,
    autoformat,
    autotable,
    error_console,
    execution_time,
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
            choices=("show", "start", "stop", "delete", "visibility", "clean"),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument("action2", nargs="?", default=None)
        parser.add_argument(
            "--clean", action="store_true", help="clean all report related"
        )
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)

    def __call__(
        self,
        id: str,
        action: Literal["show", "start", "stop", "delete", "visibility", "clean"],
        action2: Optional[str],
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
                reports["rows"] = [
                    {**x, "execution_time": execution_time(x["execution_time"])}
                    for x in reports["rows"]
                ]
                autoformat(info)
                autotable(BootstrapTable(**reports), page=page, limit=limit)
                return
        elif action == "visibility":
            if not action2 or action2 not in VISIBILITY_VALUES:
                error_console.print(
                    f"Allowed values for visibility: {VISIBILITY_VALUES}"
                )
                return 1
            info = client.patch(
                f"/monitors/{id}", json={"visibility": action2.capitalize()}
            ).json()
        elif action in ("start", "stop"):
            client.patch(f"/monitors/{id}/{action}")
            print(f"Monitor {'stopped' if action == 'stop' else 'started'}")
            return
        elif action == "clean":
            client.delete(f"/monitors/{id}/reports")
            print("Monitor reports cleaned")
            return

        autoformat(info, jsonfmt=kwargs["json"], list_separator="*" * 48)
