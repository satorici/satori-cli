import subprocess
from argparse import ArgumentParser

from .base import BaseCommand


class HelpCommand(BaseCommand):
    name = "help"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-w", "--web", action="store_true")

    def __call__(self, web: bool, **kwargs):
        if web:
            subprocess.run(["satori-docs", "--web"])
        else:
            subprocess.run(["satori-docs"])
