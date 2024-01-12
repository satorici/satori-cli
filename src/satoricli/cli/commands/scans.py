from argparse import ArgumentParser

from satoricli.api import client

from ..utils import BootstrapTable, autoformat, autotable, get_offset
from .base import BaseCommand


class ScansCommand(BaseCommand):
    name = "scans"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)

    def __call__(self, page: int, limit: int, **kwargs):
        offset = get_offset(page, limit)
        repos = client.get("/scans", params={"offset": offset, "limit": limit}).json()

        if not kwargs["json"]:
            # Group repos by team name
            autotable(BootstrapTable(**repos), page=page, limit=limit)
        else:
            autoformat(repos, jsonfmt=kwargs["json"], list_separator="-" * 48)
