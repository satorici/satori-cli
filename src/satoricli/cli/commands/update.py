import subprocess
import sys
from argparse import ArgumentParser

from rich.prompt import Confirm

from satoricli.cli.utils import console

from .base import BaseCommand


class UpdateCommand(BaseCommand):
    name = "update"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "-y",
            action="store_true",
            dest="confirmed",
            help="Update without confirmation",
        )

    def __call__(self, confirmed: bool, **kwargs):
        console.print(f"Going to run: {sys.executable} -m pip install -U satori-ci")

        if not confirmed and not Confirm.ask("Do you want to continue", default="y"):
            return

        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "satori-ci"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        return proc.returncode
