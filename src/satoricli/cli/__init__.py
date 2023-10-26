import sys
from datetime import datetime
from importlib import metadata

import httpx
from packaging import version

from ..api import configure_client
from ..utils import load_config
from .commands.root import RootCommand
from .utils import error_console
from .commands.config import ConfigCommand

VERSION = metadata.version("satori-ci")


def check_for_update():
    """Verify the current version and the latest version"""

    try:
        response = httpx.get("https://pypi.org/pypi/satori-ci/json")
        response.raise_for_status()
    except Exception:
        error_console.print("[yellow]WARNING:[/] Unable to get latest version.")
        return

    latest = response.json()["info"]["version"]

    if version.parse(latest) > version.parse(VERSION):
        error_console.print(
            f"[yellow]WARNING:[/] Newer version available v{latest}, update with:",
            "satori update",
        )


def main():
    timestamp = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    error_console.print(
        f"[dim]Satori CI {VERSION} - Automated Cloud Testing - "
        f"Started on {timestamp}"
    )

    check_for_update()

    root = RootCommand()
    args = root.parse_args()

    if config := load_config().get(args["profile"]):
        configure_client(**config)
    elif not isinstance(args["func"], ConfigCommand):
        # Allow config cmd only if profile not found
        error_console.print(
            f"[error]ERROR:[/] Profile {args['profile']} not found.",
            "These are the profiles available:",
        )
        for key in load_config():
            error_console.print(key)
        sys.exit(1)

    try:
        sys.exit(root.run(args))
    except Exception as e:
        error_console.print(e)
        sys.exit(1)
