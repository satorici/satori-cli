from argparse import ArgumentParser
from importlib import metadata

from ..arguments import json_arg, profile_arg
from .base import BaseCommand
from .config import ConfigCommand
from .dashboard import DashboardCommand
from .help import HelpCommand
from .monitor import MonitorCommand
from .outputs import OutputsCommand
from .playbook import PlaybookCommand
from .repo import RepoCommand
from .report import ReportCommand
from .run import RunCommand
from .team import TeamCommand
from .update import UpdateCommand

VERSION = metadata.version("satori-ci")


class RootCommand(BaseCommand):
    subcommands = (
        ConfigCommand,
        RunCommand,
        ReportCommand,
        MonitorCommand,
        OutputsCommand,
        RepoCommand,
        PlaybookCommand,
        DashboardCommand,
        TeamCommand,
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
