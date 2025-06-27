from argparse import ArgumentParser
import subprocess
import sys
import webbrowser

from satoricli.utils import load_config, save_config

from .base import BaseCommand
from ..utils import console, error_console


class InstallCommand(BaseCommand):
    name = "install"

    def register_args(self, parser: ArgumentParser):
        pass

    def __call__(self, **kwargs):
        # Open browser to get token
        url = "https://satori.ci/user-settings/#user-api-token"
        webbrowser.open(url)
        console.print(
            "Log in to Satori CI and get your token from the 'User API Token' page at: [b blue]{url}[/]"
        )

        # Get token from user
        token = console.input("[warning]Copy and paste your token here: [/]")
        token = token.strip()

        # Save token
        config = load_config()
        config.setdefault(kwargs["profile"], {})["token"] = token
        console.print(f"\nSatori CLI Token updated for profile {kwargs['profile']}")
        save_config(config)

        # Install v2
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "git+https://github.com/satorici/cli-v2",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0: # error
            error_console.print("\n[bold red]Failed to install Satori CLI v2:[/]")
            error_console.print(result.stderr)
            return 1
        else:  # ok
            console.print("\nSatori CLI v2 installed successfully")
