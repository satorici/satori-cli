import platform
import subprocess
import sys
from argparse import ArgumentParser

import httpx

from satoricli.cli.utils import console

from .base import BaseCommand


class UpdateCommand(BaseCommand):
    name = "update"

    def register_args(self, parser: ArgumentParser):
        pass

    def __call__(self, **kwargs):
        console.print(f"Going to run: {sys.executable} -m pip install -U satori-ci")

        # Get last version from pypi and avoid to install it from cache
        response = httpx.get("https://pypi.org/pypi/satori-ci/json")
        latest = response.json()["info"]["version"]

        args = [sys.executable, "-m", "pip", "install", "-U", f"satori-ci=={latest}"]

        if platform.system() == "Windows":
            subprocess.Popen(args)
            return

        proc = subprocess.run(args, stdout=sys.stdout, stderr=sys.stderr)

        return proc.returncode
