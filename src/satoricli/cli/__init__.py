import sys
from datetime import datetime
from importlib import metadata
from os import environ

import httpx
from packaging import version

from ..api import configure_client
from ..exceptions import SatoriRequestError
from ..utils import load_config
from .commands.config import ConfigCommand
from .commands.root import RootCommand
from .utils import error_console

VERSION = metadata.version("satori-ci")


def check_for_update():
    """Verify the current version and the latest version"""

    try:
        response = httpx.get("https://pypi.org/pypi/satori-ci/json")
        response.raise_for_status()
    except Exception:
        error_console.print("[warning]WARNING:[/] Unable to get latest version.")
        return

    latest = response.json()["info"]["version"]

    if version.parse(latest) > version.parse(VERSION):
        error_console.print(
            f"[warning]WARNING:[/] Newer version available v{latest}, update with:",
            "satori update",
        )


def main():
    timestamp = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    error_console.print(
        f"[dim]Satori CI {VERSION} - Automated Cloud Testing - "
        f"Started on {timestamp}"
    )

    if environ.get("SATORI_CLI_NO_UPDATE_CHECK") != "1":
        check_for_update()

    root = RootCommand()
    args = root.parse_args()

    try:
        config = load_config().get(args["profile"])
    except Exception as e:
        error_console.print(
            f"[error]ERROR:[/] Your .satori_credentials.yml file in your home is corrupted."
        )
        sys.exit(1)

    if config:
        try:
            configure_client(**config)
        except Exception as e:
            error_console.print(
                f"[error]ERROR:[/] Cannot find your profile in your .satori_credentials.yml file. Is it corrupted?"
            )
            sys.exit(1)
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
    except SatoriRequestError as e:
        error_console.print(f"ERROR: {e}")
        error_console.print(f"Status code: {e.status_code}")
        sys.exit(1)
    except Exception as e:
        error_console.print(e)
        sys.exit(1)
