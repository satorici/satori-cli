from argparse import ArgumentParser
from importlib import metadata

from ..arguments import json_arg, profile_arg
from .base import BaseCommand
from .config import ConfigCommand
from .dashboard import DashboardCommand
from .help import HelpCommand
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
from .team import TeamCommand
from .teams import TeamsCommand
from .update import UpdateCommand

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
    )
    name = "satori"
    global_options = (profile_arg, json_arg)
    default_subcommand = DashboardCommand

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "-v", "--version", action="version", version=f"%(prog)s {VERSION}"
        )
