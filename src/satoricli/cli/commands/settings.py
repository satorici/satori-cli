from argparse import ArgumentParser
from typing import Literal, get_args

from satoricli.api import client
from satoricli.cli.utils import console
from rich.prompt import Prompt

from .base import BaseCommand

VALID_KEYS = Literal[
    "default",
    "datadog",
    "discord",
    "email",
    "slack",
    "telegram",
]


class SettingsCommand(BaseCommand):
    name = "settings"

    def register_args(self, parser: ArgumentParser):
        _ = parser.add_argument(
            "key",
            metavar="KEY",
            choices=get_args(VALID_KEYS),
            nargs="?",
        )
        _ = parser.add_argument("value", metavar="VALUE", nargs="?")

    def __call__(self, key: VALID_KEYS, value: None | str, **kwargs) -> None:
        self.team: str = kwargs.get("team") or "Private"
        while True:
            display_options: tuple[VALID_KEYS] = get_args(VALID_KEYS)
            for i, option in enumerate(display_options, 0):
                val = self.get_settings(option)
                console.print(f"{i}. {option}: {val}")

            console.print()
            console.print("9. exit")
            console.print()

            choices = [str(i) for i in range(len(display_options))] + ["9"]
            choice = Prompt.ask("Choose an option", choices=choices)
            match choice:
                case "9":
                    break
                case "0":
                    console.print("[bold red]Not implemented[/bold red]")
                case "1":
                    self.update_settings("datadog_api_key", "Datadog API key")
                    console.print("Datadog API key updated")
                case "2":
                    self.update_settings("discord_channel", "Discord channel ID")
                    console.print("Discord channel updated")
                case "3":
                    self.update_settings("notification_email", "Notification email")
                    console.print("Notification email updated")
                case "4":
                    self.update_settings("slack_workspace", "Slack workspace")
                    console.print("Slack workspace updated")
                    self.update_settings("slack_channel", "Slack channel")
                    console.print("Slack channel updated")
                case "5":
                    self.update_settings("telegram_channel", "Telegram channel")
                    console.print("Telegram channel updated")
                case _:
                    pass

    def get_settings(self, key: VALID_KEYS):
        if key == "default":
            return "not set"
        get_config = []
        if key == "datadog":
            get_config = ["datadog_api_key"]
        if key == "discord":
            get_config = ["discord_channel"]
        if key == "email":
            get_config = ["notification_email"]
        if key == "slack":
            get_config = ["slack_workspace", "slack_channel"]
        if key == "telegram":
            get_config = ["telegram_channel"]
        info = []
        for config in get_config:
            val = client.get(f"/teams/{self.team}/config/{config}").text
            info.append(val or "not set")
        return " | ".join(info)

    def update_settings(self, key: str, prompt: str) -> None:
        _ = client.put(
            f"/teams/{self.team}/config",
            json={
                "name": key,
                "value": Prompt.ask(prompt),
            },
        )
