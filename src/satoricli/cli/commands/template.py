from argparse import ArgumentParser
from typing import Literal, get_args

from httpx._models import Response
from rich.prompt import Prompt

from satoricli.api import client
from satoricli.cli.utils import autoformat, console

from .base import BaseCommand

ACTIONS = Literal["show", "create", "update", "delete"]


class TemplateCommand(BaseCommand):
    name = "template"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id")
        parser.add_argument(
            "action",
            nargs="?",
            choices=get_args(ACTIONS),
            default="show",
        )

    def __call__(self, id: str, action: ACTIONS, **kwargs):
        if id == "create":
            action = "create"
        if action == "show":
            info = client.get(f"/templates/{id}").json()
            content = info.pop("content")
            autoformat(info)
            console.print("Content:\n", content)
        elif action == "update":
            console.print("Please use the web interface to update templates")
        elif action == "create":
            title = Prompt.ask("Enter the template title")
            description = Prompt.ask("Enter the template description")
            severity = Prompt.ask(
                "Select the template severity",
                choices=["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL", "BLOCKER"],
            )
            console.print(
                "Enter your text (press [b]Enter[/] on an empty line to finish):"
            )
            lines = []
            while True:
                line = console.input()
                if not line:
                    break
                lines.append(line)
            multiline_text = "\n".join(lines)
            res: Response = client.post(
                "/templates",
                json={
                    "title": title,
                    "description": description,
                    "severity": severity,
                    "content": multiline_text,
                },
            )
            if res.is_success:
                console.print("Template created")
            else:
                console.print(f"Error creating template: {res.text}")
        elif action == "delete":
            client.delete(f"/templates/{id}")
