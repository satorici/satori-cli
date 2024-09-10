import platform
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

        args = [sys.executable, "-m", "pip", "install", "-U", "satori-ci"]

        if platform.system() == "Windows":
            subprocess.Popen(args)
            return

        proc = subprocess.run(args, stdout=sys.stdout, stderr=sys.stderr)

        return proc.returncode
