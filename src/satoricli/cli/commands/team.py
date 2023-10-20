from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client
from satoricli.cli.utils import autoformat, console

from .base import BaseCommand


class TeamCommand(BaseCommand):
    name = "team"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("--role", default="READ", help="User role")

        # Use with the add command
        parser.add_argument("--repo", help="Repo name")
        parser.add_argument("--email", help="User email")
        parser.add_argument("--github", help="Github user name")
        parser.add_argument("--monitor", help="Monitor id")

        parser.add_argument("id", nargs="?")
        parser.add_argument(
            "action",
            nargs="?",
            choices=(
                "show",
                "create",
                "members",
                "repos",
                "get_config",
                "set_config",
                "get_token",
                "refresh_token",
                "delete",
                "add",
            ),
            default="show",
        )
        parser.add_argument("config_name", nargs="?")
        parser.add_argument("config_value", nargs="?")

    def __call__(
        self,
        id: Optional[str],
        action: Literal[
            "show",
            "create",
            "members",
            "repos",
            "get_config",
            "set_config",
            "get_token",
            "refresh_token",
            "delete",
            "add",
        ],
        role: Optional[str],
        repo: Optional[str],
        email: Optional[str],
        github: Optional[str],
        monitor: Optional[str],
        config_name: Optional[str],
        config_value: Optional[str],
        **kwargs,
    ):
        if action == "show":
            info = client.get("/teams").json()
        elif action == "create":
            info = client.post(f"/teams/{id}").json()
        elif action == "members":
            info = client.get(f"/teams/{id}/members").json()
        elif action == "add":
            if email:
                info = client.post(
                    f"/teams/{id}/members", json={"email": email, "role": role}
                ).json()
            elif github:
                info = client.post(
                    f"/teams/{id}/members", json={"github": github, "role": role}
                ).json()
            elif repo:
                info = client.post(f"/teams/{id}/repos", json={"repo": repo}).json()
            elif monitor:
                info = client.post(
                    f"/teams/{id}/monitors", json={"monitor": monitor}
                ).json()
            else:
                raise Exception("Use --repo, --member or --monitor")
        elif action == "repos":
            info = client.get(f"/teams/{id}/repos").json()["rows"]
        elif action == "get_config":
            info = client.get(f"/teams/{id}/config/{config_name}").json()
        elif action == "set_config":
            info = client.put(
                f"/teams/{id}/config",
                json={"name": config_name, "value": config_value},
            ).json()
        elif action == "get_token":
            info = client.get(f"/teams/{id}/token").json()
        elif action == "refresh_token":
            info = client.put(f"/teams/{id}/token").json()
        elif action == "delete":
            if member:
                client.request("DELETE", f"/teams/{id}/members", json={"email": member})
                console.print("Team member deleted")
            else:
                client.delete(f"/teams/{id}")
                console.print("Team deleted")
            return

        autoformat(info, jsonfmt=kwargs["json"], list_separator="*" * 48, table=True)
