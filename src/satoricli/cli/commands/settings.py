from argparse import ArgumentParser
from typing import Literal, TypeAlias, get_args

from satoricli.api import client
from satoricli.cli.utils import console
from rich.prompt import Prompt

from .base import BaseCommand

VALID_KEYS: TypeAlias = Literal[
    "default",
    "datadog",
    "discord",
    "email",
    "slack",
    "telegram",
]


class SettingsCommand(BaseCommand):
    name: str = "settings"

    def register_args(self, parser: ArgumentParser) -> None:
        _ = parser.add_argument(
            "key",
            metavar="KEY",
            choices=get_args(VALID_KEYS),
            nargs="?",
        )
        _ = parser.add_argument("value", metavar="VALUE", nargs="?")

    def __call__(
        self, key: VALID_KEYS | None = None, value: str | None = None, **kwargs
    ) -> None:
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
                    console.print(
                        "To set up Discord, you need to add the bot to your server and get the channel ID.\n\n"
                        + "Invite the bot to the server with the following link:\n"
                        + "[cyan b]https://discord.com/api/oauth2/authorize?client_id=1038196776752128131&permissions=2048&scope=bot[/]"
                    )
                    _ = input(
                        "After inviting the bot to your channel, press any key to continue..."
                    )
                    console.print(
                        "\nTo enable Developer mode and get your channel ID follow these instructions:\n"
                        + "[cyan b]https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID[/]"
                    )
                    self.update_settings(
                        "discord_channel", "Copy and paste the Discord channel ID here"
                    )
                    console.print("Discord channel updated")
                case "3":
                    self.update_settings(
                        "notification_email", "Notification emails (comma separated)"
                    )
                    console.print("Notification email updated")
                case "4":
                    console.print(
                        "To set up Slack, you need to add the bot to your workspace and invite it to the channel.\n\n"
                        + "You can invite the bot to the workspace by opening this link:\n"
                        + "[cyan b]https://satori.ci/api/authorise/slack[/]\n\n"
                        + "You can invite the bot to the channel by typing the following command: [b]/invite @SatoriCIBot[/]"
                    )
                    _ = input(
                        "After inviting the bot to your channel, press any key to continue..."
                    )
                    console.print(
                        "\nYou can find the workspace ID in the URL of your workspace, e.g.\n"
                        + "[cyan b]https://app.slack.com/client/<workspace_id>/channels[/]"
                    )
                    self.update_settings(
                        "slack_workspace", "Enter your Slack workspace ID"
                    )
                    console.print("Slack workspace updated")
                    self.update_settings(
                        "slack_channel", "Enter your Slack channel ID(e.g. #general)"
                    )
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
        values = []
        for config in get_config:
            val = client.get(f"/teams/{self.team}/config/{config}").text
            values.append(val or "not set")
        return " | ".join(values)

    def update_settings(self, key: str, prompt: str) -> None:
        _ = client.put(
            f"/teams/{self.team}/config",
            json={
                "name": key,
                "value": Prompt.ask(prompt),
            },
        )
