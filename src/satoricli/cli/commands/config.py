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
            choices=("token", "host", "timeout"),
            nargs="?",
        )
        parser.add_argument("value", metavar="VALUE", nargs="?")
        parser.add_argument(
            "-d", "--delete", action="store_true", help="delete config key"
        )
        parser.add_argument("--profiles", action="store_true")

    def __call__(
        self,
        key: Optional[str],
        value: Optional[str],
        delete: bool,
        profiles: bool,
        **kwargs,
    ):
        config = load_config()
        profile = kwargs["profile"]

        if profiles:
            for key in config:
                console.print(key)
            return

        if delete and key:
            del config[profile][key]
            save_config(config)
            return
        elif delete and not key:
            console.print("Must provide a key to delete")
            return 1

        if not key:
            console.print(config[profile])
            return

        if not value:
            console.print(config[profile][key])
            return

        config.setdefault(profile, {})[key] = value
        console.print(f"{key} updated for profile {profile}")
        save_config(config)
