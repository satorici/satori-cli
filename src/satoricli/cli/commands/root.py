from argparse import ArgumentParser
from functools import partial
from importlib import metadata

from rich.console import Group
from rich.table import Column, Table

from ..arguments import debug_arg, export_arg, json_arg, profile_arg, team_arg, config_arg
from .base import BaseCommand
from .config import ConfigCommand
from .dashboard import DashboardCommand
from .help import HelpCommand
from .install import InstallCommand
from .local import LocalCommand
from .monitor import MonitorCommand
from .monitors import MonitorsCommand
from .outputs import OutputsCommand
from .playbook import PlaybookCommand
from .playbooks import PlaybooksCommand
from .repo import RepoCommand
from .report import ReportCommand
from .reports import ReportsCommand
from .repos import ReposCommand
from .run import RunCommand
from .scan import ScanCommand
from .scans import ScansCommand
from .team import TeamCommand
from .teams import TeamsCommand
from .update import UpdateCommand
from .shards import ShardsCommand

VERSION = metadata.version("satori-ci")


class RootCommand(BaseCommand):
    subcommands = (
        ConfigCommand,
        RunCommand,
        ReportCommand,
        ReportsCommand,
        MonitorCommand,
        MonitorsCommand,
        OutputsCommand,
        RepoCommand,
        ReposCommand,
        ScanCommand,
        PlaybookCommand,
        PlaybooksCommand,
        DashboardCommand,
        TeamCommand,
        TeamsCommand,
        HelpCommand,
        UpdateCommand,
        LocalCommand,
        ScansCommand,
        ShardsCommand,
        InstallCommand
    )
    name = "satori"
    global_options = (profile_arg, json_arg, debug_arg, export_arg, team_arg, config_arg)
    default_subcommand = DashboardCommand

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "-v", "--version", action="version", version=f"%(prog)s {VERSION}"
        )
        parser.add_argument(
            "--pending", action="store_true", help="Show pending actions"
        )
        parser.add_argument("--public", action="store_true", help="Fetch public")

    def help(self):
        def add_rows(table: Table, rows):
            for row in rows:
                table.add_row(*row)

        def cols():
            return Column(ratio=1), Column(ratio=1)

        HelpTable = partial(Table, expand=True, show_header=False)
        tables = []

        tables.append(
            intro := HelpTable(*cols(), title="Install, Update and Configure")
        )
        rows = [
            ("pip3 install satori-ci", "Install the latest version"),
            ("satori update", "Update to the latest version"),
            (
                'satori config token "USERTOKEN"',
                "Configure your user token as your default profile",
            ),
            (
                'satori config token "TEAMTOKEN" --profile TEAM',
                "Configure your team token on your team profile",
            ),
        ]
        add_rows(intro, rows)

        tables.append(run_async := HelpTable(*cols(), title="Run asyncronously"))
        rows = [
            (
                "satori run ./",
                "Upload the current dir and run the playbook .satori.yml",
            ),
            ("satori run playbook.yml", "Upload the playbook and run it"),
            (
                'satori run ./ --playbook="satori://..."',
                "Upload the current dir and run the specified playbook",
            ),
        ]
        add_rows(run_async, rows)

        tables.append(
            run_sync := HelpTable(
                *cols(), title="Run syncronously using these parameters"
            )
        )
        rows = [
            ("--sync", "Show the result"),
            ("--report", "Show the report"),
            ("--output", "Show the output"),
            (
                "--files",
                "Download the files created if the setting files was set to True",
            ),
        ]
        add_rows(run_sync, rows)

        tables.append(
            params := HelpTable(*cols(), title="Run playbooks with variables")
        )
        rows = [
            (
                '--data VAR="This is the value of VAR"',
                "Provide values for the undefined playbook variables",
            )
        ]
        add_rows(params, rows)

        tables.append(playbooks := HelpTable(*cols(), title="Playbooks"))
        rows = [
            ("satori playbooks", "List your private playbooks"),
            ("satori playbooks --public", "List the public playbooks"),
            ("satori playbook ID", "Show a certain playbook"),
            ("satori playbook ID public", "Toggles the playbook's visibility"),
            ("satori playbook ID delete", "Delete the playbook"),
        ]
        add_rows(playbooks, rows)

        tables.append(dashboards := HelpTable(*cols(), title="Dashboards"))
        rows = [
            ("satori", "Show your general dashboard"),
            ("satori team TEAM", "Show your TEAM dashboard"),
        ]
        add_rows(dashboards, rows)

        tables.append(reports := HelpTable(*cols(), title="Reports"))
        rows = [
            ("satori reports", "List reports"),
            ("satori report ID", "Show the report ID"),
            ("satori report ID --json", "Show the JSON of the report ID"),
            ("satori report ID output", "Show the output of the report ID"),
            (
                "satori report ID output --json",
                "Show the JSON's output of the report ID",
            ),
            (
                "satori report ID files",
                "Download the files created (if Files was set to True in settings)",
            ),
            ("satori report ID public", "Toggles the report's visibility"),
            ("satori report ID stop", "Stop the current report execution"),
            ("satori report ID delete", "Delete the report ID"),
        ]
        add_rows(reports, rows)

        tables.append(repos := HelpTable(*cols(), title="Repos"))
        rows = [
            ("satori repos", "List the repositories connected to CI or tested"),
            (
                "satori repo GithubUser/Repo",
                "Shows the repository Visibility, CI, Playbook, Status, Result and its team.",
            ),
            (
                "satori repo GithubUser/Repo run",
                "Run the repository's playbook on the latest commit",
            ),
            (
                'satori repo GithubUser/Repo run --playbook="satori://..."',
                "Run another playbook on the latest commit",
            ),
            (
                "satori repo GithubUser/Repo commits",
                "Show the list of commits and the reports associated",
            ),
        ]
        add_rows(repos, rows)

        tables.append(monitors := HelpTable(*cols(), title="Monitors"))
        rows = [
            ("satori monitors", "List monitors"),
            ("satori monitor ID", "List the reports associated to a monitor ID"),
            ("satori monitor ID stop", "Stop a monitor ID"),
            ("satori monitor ID start", "Start a monitor ID"),
            (
                "satori monitor ID clean",
                "Delete the reports associated to the monitor ID",
            ),
            ("satori monitor ID delete", "Delete the monitor ID"),
            ("satori monitor ID public", "Toggles the monitor's visibility"),
        ]
        add_rows(monitors, rows)

        tables.append(scans := HelpTable(*cols(), title="Scans"))
        rows = [
            ("satori scans", "List scans"),
            (
                "satori scan GithubUser/Repo [-c N]",
                "Scan the Github repository with the repository's playbook a coverage of 1 (default) to 100",
            ),
            (
                'satori scan GithubUser/Repo [--playbook="satori://..."]',
                "Scan the Github repository with a different playbook",
            ),
            (
                "satori scan GithubUser/Repo check-commits",
                "Get the repository commits before scanning",
            ),
            (
                "satori scan GithubUser/Repo check-forks",
                "Get the repository forks before scanning",
            ),
            (
                "satori scan ID status",
                "Show the status of the scan",
            ),
            ("satori scan ID stop", "Stop the scan on the repo"),
            (
                "satori scan ID start",
                "Start a previously stopped scan",
            ),
            (
                "satori scan ID clean",
                "Delete the reports associated to the scan",
            ),
            ("satori scan ID delete", "Delete the scan"),
            ("satori scan ID public", "Toggle the scan's visibility"),
        ]
        add_rows(scans, rows)

        tables.append(teams := HelpTable(*cols(), title="Teams"))
        rows = [
            ("satori teams", "List your teams"),
            ("satori team TEAM", "Show the TEAM dashboard"),
            ("satori team TEAM create", "Create a new team named TEAM"),
            ("satori team TEAM members", "List your TEAM members"),
            ("satori team TEAM monitors", "List your TEAM monitors"),
            ("satori team TEAM repos", "List your TEAM repositories"),
            ("satori team TEAM reports", "List your TEAM reports"),
            ("satori team TEAM settings", "List your TEAM settings"),
            ("satori team TEAM get_config NAME", "Show your TEAM's config setting"),
            ("satori team TEAM set_config NAME VALUE", "Set your TEAM CONFIG setting"),
            (
                'satori team TEAM add --github="GithubUser"',
                "Owners and admins can add users via Github to the TEAM",
            ),
            ('--role="READ"', "use the role READ (default) or ADMIN"),
            (
                'satori team TEAM add --email="usr@example.com"',
                "Owners and admins can add users via Email to the TEAM",
            ),
            ('--role="READ"', "use the role READ (default) or ADMIN"),
            (
                'satori team TEAM add --monitor="MONITORID"',
                "Add the monitor ID to your TEAM",
            ),
            (
                'satori team TEAM add --repo="GithubUser/repo"',
                "Add the repo to your TEAM",
            ),
            (
                'satori team TEAM del --github="GithubUser"',
                "Delete the GithubUser from your TEAM",
            ),
            (
                'satori team TEAM del --email="usr@example.com"',
                "Delete the email from the TEAM",
            ),
            (
                'satori team TEAM del --repo="GithubUser/repo"',
                "Delete the repo from the TEAM",
            ),
            (
                'satori team TEAM del --monitor="MONITORID"',
                "Delete the monitor from the TEAM",
            ),
            ("satori team TEAM delete", "Delete the TEAM"),
        ]
        add_rows(teams, rows)

        tables.append(shards := HelpTable(*cols(), title="Shards"))
        rows = [
            ("satori shards --shard X/Y --input INPUT", "Divide massive datasets into smaller chunks for distributed processing"),
            ("--shard X/Y", "Shard index X out of Y total shards (required)"),
            ("--input INPUT", "Input file path or direct IP/CIDR/range/domain/URL (required)"),
            ("--exclude PATH or ENTRY", "Exclusion file path or direct IP/CIDR/range/domain/URL to exclude"),
            ("--seed N", "Seed for deterministic pseudorandom distribution (default: 1)"),
            ("--results PATH", "Output file path (writes to stdout if omitted)"),
        ]
        add_rows(shards, rows)

        return Group(*tables)
