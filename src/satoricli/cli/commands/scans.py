from argparse import ArgumentParser

from satoricli.api import client

from ..utils import BootstrapTable, autoformat, autotable
from .base import BaseCommand


class ScansCommand(BaseCommand):
    name = "scans"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)
        parser.add_argument("--public", action="store_true", help="Fetch public scans")

    def __call__(self, page: int, limit: int, public: bool, **kwargs):
        url = "/scan/public" if public else "/scan"
        scans = client.get(url, params={"page": page, "limit": limit}).json()

        if not kwargs["json"]:
            # Group scans by team name
            autotable(BootstrapTable(**scans), page=page, limit=limit, widths=(16,))
        else:
            autoformat(scans, jsonfmt=kwargs["json"], list_separator="-" * 48)
