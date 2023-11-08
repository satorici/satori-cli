from argparse import ArgumentParser

from satoricli.api import client
from satoricli.cli.utils import autoformat

from .base import BaseCommand


class TeamsCommand(BaseCommand):
    name = "teams"

    def register_args(self, parser: ArgumentParser):
        pass

    def __call__(self, **kwargs):
        info = client.get("/teams").json()
        autoformat(info, jsonfmt=kwargs["json"], list_separator="*" * 48, table=True)
