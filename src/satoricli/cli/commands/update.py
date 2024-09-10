import subprocess
import sys
from argparse import ArgumentParser

from satoricli.cli.utils import console

from .base import BaseCommand


class UpdateCommand(BaseCommand):
    name = "update"

    def register_args(self, parser: ArgumentParser):
        pass

    def __call__(self, **kwargs):
        console.print(f"Going to run: {sys.executable} -m pip install -U satori-ci")

        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "satori-ci"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        return proc.returncode
