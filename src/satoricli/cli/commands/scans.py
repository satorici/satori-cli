from argparse import ArgumentParser

from satoricli.api import client

from ..utils import BootstrapTable, autoformat, autotable
from .base import BaseCommand


class ScansCommand(BaseCommand):
    name = "scans"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)

    def __call__(self, page: int, limit: int, **kwargs):
        repos = client.get("/scan", params={"page": page, "limit": limit}).json()

        if not kwargs["json"]:
            # Group repos by team name
            autotable(BootstrapTable(**repos), page=page, limit=limit, widths=(16,))
        else:
            autoformat(repos, jsonfmt=kwargs["json"], list_separator="-" * 48)
