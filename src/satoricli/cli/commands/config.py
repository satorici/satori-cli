from argparse import ArgumentParser
from typing import Optional

from satoricli.cli.utils import console
from satoricli.utils import load_config, save_config

from .base import BaseCommand


class ConfigCommand(BaseCommand):
    name = "config"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "key",
            metavar="KEY",
            choices=("token", "host", "timeout", "default_team"),
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
            del config[kwargs["profile"]][key]
            save_config(config)
            return
        elif delete and key is None:
            console.print("Must provide a key to delete")
            return 1

        if key is None:
            console.print(config[kwargs["profile"]])
            return

        if value is None:
            console.print(config[kwargs["profile"]][key])
            return

        config.setdefault(kwargs["profile"], {})[key] = value
        console.print(f"{key} updated for profile {kwargs['profile']}")
        save_config(config)
