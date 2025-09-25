from argparse import ArgumentParser
from typing import Optional

from satoricli.cli.utils import console, error_console
from satoricli.utils import load_config, save_config

from .base import BaseCommand


class ConfigCommand(BaseCommand):
    name = "config"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "key",
            metavar="KEY",
            choices=("token", "host", "timeout", "default_team", "width"),
            nargs="?",
        )
        parser.add_argument("value", metavar="VALUE", nargs="?")
        parser.add_argument(
            "-d", "--delete", action="store_true", help="delete config key"
        )

    def __call__(
        self, key: Optional[str], value: Optional[str], delete: bool, **kwargs
    ):
        config = load_config()

        if delete and key:
            profile_config = config.get(kwargs["profile"], {})
            if key in profile_config:
                del config[kwargs["profile"]][key]
                save_config(config)
                console.print(f"{key} deleted from profile {kwargs['profile']}")
            else:
                console.print(f"{key} not found in profile {kwargs['profile']}")
            return
        elif delete and key is None:
            console.print("Must provide a key to delete")
            return 1

        if key is None:
            console.print(config[kwargs["profile"]])
            return

        if value is None:
            try:
                console.print(config[kwargs["profile"]][key])
            except KeyError:
                error_console.print(
                    f"ERROR: {key} missing in profile {kwargs['profile']}"
                )
            return 1

        if value == "":
            error_console.print("ERROR: Empty value")
            return 1

        # Special validation for width
        if key == "width":
            try:
                width_int = int(value)
                if width_int <= 0:
                    console.print("Error: width must be a positive integer")
                    return 1
                config.setdefault(kwargs["profile"], {})[key] = width_int
                console.print(
                    f"{key} updated to {width_int} for profile {kwargs['profile']}"
                )
            except ValueError:
                if value == "auto":
                    config.setdefault(kwargs["profile"], {})[key] = None
                    console.print(
                        f"{key} updated to auto for profile {kwargs['profile']}"
                    )
                else:
                    console.print("Error: width must be a valid integer")
                    return 1
        else:
            config.setdefault(kwargs["profile"], {})[key] = value
            console.print(f"{key} updated for profile {kwargs['profile']}")

        save_config(config)
        return 0
