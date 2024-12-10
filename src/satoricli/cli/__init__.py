import re
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
from .utils import console, error_console, log, logging

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
        f"[dim]Satori CI {VERSION} - Automated Testing - "
        f"Started on {timestamp}"
    )

    if environ.get("SATORI_CLI_NO_UPDATE_CHECK") != "1":
        check_for_update()

    root = RootCommand()
    args = root.parse_args()

    if len(sys.argv) > 1 and sys.argv[1] == "update":
        try:
            exit_code = root.run(args)
            sys.exit(exit_code)
        except Exception as e:
            error_console.print(f"Error during update: {e}")
            sys.exit(1)

    try:
        config = load_config(args.get("config")).get(args["profile"])
    except Exception as e:
        if not isinstance(args["func"], ConfigCommand):
            error_console.print(
                f"[error]ERROR:[/] Your .satori_credentials.yml file is corrupted or not found."
            )
            sys.exit(1)
        else:
            config = None

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
        for key in load_config(args.get("config")):
            error_console.print(key)
        sys.exit(1)

    if config:
        config["team"] = args["team"]
        try:
            configure_client(**config)
        except Exception as e:
            error_console.print(
                f"[error]ERROR:[/] Cannot find your profile in your .satori_credentials.yml file. Is it corrupted?"
            )
            sys.exit(1)

    # Set debug mode
    if args["debug"]:
        log.setLevel(logging.DEBUG)

    try:
        exit_code = root.run(args)
        export = args["export"]
        if export:
            if export == "html":
                content = console.export_html()
            elif export == "svg":
                content = console.export_svg(title="satori-cli")
                # remove non xml utf-8 chars
                regex = (
                    r"[^\x09\x0A\x0D\x20-\xFF\x85\xA0-\uD7FF\uE000-\uFDCF\uFDE0-\uFFFD]"
                )
                content = re.sub(regex, "", content, flags=re.MULTILINE)
            else:
                content = console.export_text()
            with open(f"output.{export}", "w") as f:
                f.write(content)
        sys.exit(exit_code)
    except SatoriRequestError as e:
        error_console.print(f"ERROR: {e}")
        error_console.print(f"Status code: {e.status_code}")
        sys.exit(1)
    except Exception as e:
        if args["debug"]:
            log.exception(e)
        else:
            error_console.print(e)
        sys.exit(1)
