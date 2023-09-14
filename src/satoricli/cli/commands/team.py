from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client, configure_client
from satoricli.cli.utils import autoformat, console
from satoricli.utils import load_config

from .base import BaseCommand


class TeamCommand(BaseCommand):
    name = "team"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("--email", help="User email")
        parser.add_argument("--role", default="READ", help="User role")
        parser.add_argument("--repo", help="Repo name")
        parser.add_argument("id", nargs="?")
        parser.add_argument(
            "action",
            nargs="?",
            choices=(
                "show",
                "create",
                "members",
                "add_member",
                "repos",
                "add_repo",
                "get_config",
                "set_config",
                "get_token",
                "refresh_token",
                "delete",
                "del_member",
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
            "add_member",
            "repos",
            "add_repo",
            "get_config",
            "set_config",
            "get_token",
            "refresh_token",
            "delete",
            "del_member",
        ],
        email: Optional[str],
        role: Optional[str],
        repo: Optional[str],
        config_name: Optional[str],
        config_value: Optional[str],
        **kwargs,
    ):
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])

        if action == "show":
            info = client.get("/teams").json()
        elif action == "create":
            info = client.post(f"/teams/{id}").json()
        elif action == "members":
            info = client.get(f"/teams/{id}/members").json()
        elif action == "add_member":
            info = client.post(
                f"/teams/{id}/members", json={"email": email, "role": role}
            ).json()
        elif action == "repos":
            info = client.get(f"/teams/{id}/repos").json()
        elif action == "add_repo":
            info = client.post(f"/teams/{id}/repos", json={"repo": repo}).json()
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
            client.delete(f"/teams/{id}")
            console.print("Team deleted")
            return
        elif action == "del_member":
            # TODO: Update API to take params
            client.request("DELETE", f"/teams/{id}/members", json={"email": email})
            console.print("Team member deleted")
            return

        autoformat(info, jsonfmt=kwargs["json"], list_separator="*" * 48, table=True)
