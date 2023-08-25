import sys
from datetime import datetime
from importlib import metadata

import requests
from packaging import version
from pkg_resources import DistributionNotFound, get_distribution

from .commands.root import RootCommand
from .utils import error_console

VERSION = metadata.version("satori-ci")


def upgrade():
    """Verify the current version and the latest version"""
    upgrade_required = ""

    # Name of your package
    package_names = ["satori-ci", "satori-playbook-validator", "satori-docs"]

    for package_name in package_names:
        # Get the current version
        try:
            current_version = get_distribution(package_name).version
        except DistributionNotFound:
            error_console.print(f"{package_name} is not installed.")
            current_version = None

        # Get the latest version
        latest_version = None
        try:
            response = requests.get(
                f"https://pypi.org/pypi/{package_name}/json", timeout=10
            )
            if response.status_code == 200:
                latest_version = response.json()["info"]["version"]
        except Exception:
            error_console.print(
                "[error]ERROR:[/] unable to get the latest "
                f"version of the package {package_name}."
            )

        # Compare the versions and upgrade if necessary
        if (
            current_version
            and latest_version
            and version.parse(current_version) < version.parse(latest_version)
        ):
            upgrade_required += package_name + " "
    if upgrade_required:
        error_console.print(
            "[yellow]WARNING:[/] Newer version found, upgrade with: "
            f"[b]pip3 install -U {upgrade_required}"
        )


def main():
    timestamp = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    error_console.print(
        f"[dim]Satori CI {VERSION} - Automated Software Testing Platform - "
        f"Started on {timestamp}"
    )

    upgrade()

    root = RootCommand()
    args = root.parse_args()

    try:
        sys.exit(root.run(args))
    except Exception as e:
        error_console.print(e)
        sys.exit(1)
