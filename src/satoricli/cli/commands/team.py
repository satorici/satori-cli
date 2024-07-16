from argparse import ArgumentParser
from typing import Literal, Optional

from satoricli.api import client
from satoricli.cli.utils import autoformat, autotable, console

from .base import BaseCommand
from .dashboard import DashboardCommand
from .report import ReportCommand
from ..utils import BootstrapTable, get_offset


class TeamCommand(BaseCommand):
    name = "team"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("--role", default="READ", help="User role")

        # Use with the add command
        parser.add_argument("--repo", help="Repo name")
        parser.add_argument("--email", help="User email")
        parser.add_argument("--github", help="Github user name")
        parser.add_argument("--monitor", help="Monitor id")

        parser.add_argument("id")
        parser.add_argument(
            "action",
            nargs="?",
            choices=(
                "show",
                "create",
                "members",
                "repos",
                "monitors",
                "reports",
                "get_config",
                "set_config",
                "get_token",
                "refresh_token",
                "del",
                "delete",
                "add",
                "settings",
                "playbooks",
            ),
            default="show",
        )
        parser.add_argument("config_name", nargs="?")
        parser.add_argument("config_value", nargs="?")
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)

    def __call__(
        self,
        id: str,
        action: Literal[
            "show",
            "create",
            "members",
            "repos",
            "monitors",
            "reports",
            "get_config",
            "set_config",
            "get_token",
            "refresh_token",
            "del",
            "delete",
            "add",
            "settings",
            "playbooks",
        ],
        role: Optional[str],
        repo: Optional[str],
        email: Optional[str],
        github: Optional[str],
        monitor: Optional[str],
        config_name: Optional[str],
        config_value: Optional[str],
        page: int,
        limit: int,
        **kwargs,
    ):
        if action == "show":
            info = client.get(f"/teams/{id}").json()
            return DashboardCommand.generate_dashboard(info)
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
                raise Exception("Use --github, --email, --repo or --monitor")
        elif action == "repos":
            offset = get_offset(page, limit)
            info = client.get(
                f"/teams/{id}/repos", params={"offset": offset, "limit": limit}
            ).json()
            autotable(
                BootstrapTable(**info), "b blue", False, (20, 20, None), page, limit
            )
            return
        elif action == "get_config":
            info = client.get(f"/teams/{id}/config/{config_name}").text
        elif action == "set_config":
            info = client.put(
                f"/teams/{id}/config",
                json={"name": config_name, "value": config_value},
            ).json()
        elif action == "get_token":
            info = client.get(f"/teams/{id}/token").json()
        elif action == "refresh_token":
            info = client.put(f"/teams/{id}/token").json()
        elif action == "del":
            if email:
                client.request("DELETE", f"/teams/{id}/members", json={"email": email})
                console.print("Team member deleted")
            elif repo:
                client.request("DELETE", f"/teams/{id}/repos", json={"repo": repo})
                console.print("Team repo deleted")
            elif github:
                client.request(
                    "DELETE", f"/teams/{id}/members", json={"github": github}
                )
                console.print("Team member deleted")
            else:
                raise Exception("Use --github, --email or --repo")
            return
        elif action == "delete":
            client.delete(f"/teams/{id}")
            console.print("Team deleted")
            return
        elif action == "monitors":
            info = client.get(f"/teams/{id}/monitors").json()
            if not kwargs["json"]:
                autotable(info["rows"], "b blue", widths=(20, 20, None))
                return
        elif action == "reports":
            info = client.get(f"/teams/{id}/reports").json()
            return ReportCommand.print_report_list(info["rows"])
        elif action == "settings":
            info = client.get(f"/teams/{id}/config").json()
        elif action == "playbooks":
            info = client.get(f"/teams/{id}/playbooks").json()
            if not kwargs["json"]:
                autotable(info, "b blue")
                return

        autoformat(info, jsonfmt=kwargs["json"], list_separator="*" * 48, table=True)
