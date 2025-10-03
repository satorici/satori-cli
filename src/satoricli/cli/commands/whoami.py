from argparse import ArgumentParser
from typing import Literal, get_args

from satoricli.api import client
from satoricli.cli.utils import (
    console,
)

from .base import BaseCommand

ACTIONS = Literal["show"]


class WhoamiCommand(BaseCommand):
    name = "whoami"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "action", nargs="?", choices=get_args(ACTIONS), default="show"
        )

    def __call__(
        self,
        action: ACTIONS,
        **kwargs,
    ):
        if action == "show":
            info = client.get("/users/me").json()
            console.print("Name:", info["name"])
            console.print("Display name:", info["display_name"])
            console.print("Email:", info["email"])
            console.print("Role:", info["role"].capitalize())
            console.print("Team:", info["team_name"])
            accounts = client.get("/users/accounts").json()
            for account in accounts:
                console.print(account.capitalize() + ":", accounts[account]["username"])
        return
