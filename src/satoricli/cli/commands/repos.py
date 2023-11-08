from argparse import ArgumentParser

from satoricli.api import client

from ..utils import BootstrapTable, autoformat, autotable, console, group_table
from .base import BaseCommand


class ReposCommand(BaseCommand):
    name = "repos"

    def register_args(self, parser: ArgumentParser):
        pass

    def __call__(self, **kwargs):
        info = client.get("/repos").json()

        if not kwargs["json"]:
            if info["pending"]["rows"]:
                console.rule("[b red]Pending actions", style="red")
                autotable(info["pending"]["rows"], "bold red", widths=(50, 50))
            # Group repos by team name
            group_table(BootstrapTable(**info["list"]), "team", "Private")
        else:
            autoformat(info, jsonfmt=kwargs["json"], list_separator="-" * 48)
