from argparse import ArgumentParser

from satoricli.cli.utils import console
from satoricli.utils import load_config

from .base import BaseCommand


class WidthCommand(BaseCommand):
    name = "width"

    def register_args(self, parser: ArgumentParser):
        pass  # No arguments needed, just show current width

    def __call__(self, **kwargs):
        config = load_config()
        profile = kwargs.get("profile", "default")

        profile_config = config.get(profile, {})
        current_width = profile_config.get("width")

        if current_width is not None:
            console.print(f"Current configured width for profile '{profile}': {current_width}")
        else:
            console.print(f"Width not configured for profile '{profile}'. Console width is auto-detected.")