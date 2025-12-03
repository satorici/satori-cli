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
                    default_dict: dict[str, bool] = {
                        "slack": False,
                        "discord": False,
                        "datadog": False,
                        "email": False,
                        "telegram": False,
                    }
                    user_input: str = Prompt.ask(
                        "Please select a default notification method",
                        choices=[k for k in default_dict.keys()] + ["none"],
                    )
                    if user_input != "none":
                        default_dict[user_input] = True
                    _ = client.put(f"/teams/{self.team}/logs", json=default_dict)
                    console.print("Default notification method updated\n")
                case "1":
                    console.print(
                        "To set up Datadog, you need to get an API key from your Datadog account.\n\n"
                        + "You can find your API key in the Datadog API keys page(create a new API key if needed): \n"
                        + "[cyan b]https://app.datadoghq.com/organization-settings/api-keys[/]"
                    )
                    self.update_settings(
                        "datadog_api_key", "Enter your Datadog API key"
                    )
                    console.print("Datadog API key updated")
                    self.update_settings(
                        "datadog_site",
                        "Enter your Datadog region",
                        ["us1", "us3", "us5", "eu1", "ap1", "ap2", "us1-fed"],
                    )
                    console.print("Datadog site updated\n")
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
                    console.print("Discord channel updated\n")
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
                    console.print("Slack channel updated\n")
                case "5":
                    console.print(
                        "To set up Telegram, you need to add the bot to your channel.\n\n"
                        + "Invite @satori_ci_bot as a new member to your channel."
                    )
                    _ = input(
                        "After inviting the bot to your channel, press any key to continue..."
                    )
                    console.print(
                        "Obtain the Channel ID: access your channel via the web at Telegram Web."
                        + "The Channel ID is the number that appears after the # in the URL"
                    )
                    self.update_settings(
                        "telegram_channel", "Insert the Channel ID(e.g. -15050500050)"
                    )
                    console.print("Telegram channel updated\n")
                case _:
                    pass

    def get_settings(self, key: VALID_KEYS):
        get_config = []
        if key == "default":
            logs: dict[str, bool] = client.get(f"/teams/{self.team}/logs").json()
            filtered = list(filter(lambda x: logs[x] is True, logs))
            return " | ".join(filtered) if filtered else "not set"
        if key == "datadog":
            get_config = ["datadog_api_key", "datadog_site"]
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

    def update_settings(
        self, key: str, prompt: str, choices: list[str] | None = None
    ) -> None:
        _ = client.put(
            f"/teams/{self.team}/config",
            json={
                "name": key,
                "value": Prompt.ask(prompt, choices=choices),
            },
        )
