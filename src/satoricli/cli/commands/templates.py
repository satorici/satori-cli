from argparse import ArgumentParser

from satoricli.api import client
from satoricli.cli.utils import BootstrapTable, autotable

from .base import BaseCommand


class TemplatesCommand(BaseCommand):
    name = "templates"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)

    def __call__(self, page: int, limit: int, **kwargs):
        info = client.get("/templates", params={"page": page, "limit": limit}).json()
        autotable(BootstrapTable(**info), page=page, limit=limit)
