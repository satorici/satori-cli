from trogon import tui
import click
from click.core import Context
import sys
import requests  # autoupgrade
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from importlib import metadata
from colorama import just_fix_windows_console
from rich import print
from pkg_resources import get_distribution, DistributionNotFound  # autoupgrade
from packaging import version  # autoupgrade
from dataclasses import replace

# from subprocess import call # autoupgrade
from ..classes.satori import Satori
from ..classes.utils import console
from ..classes.help_gui import HelpGui, DOCS_FOLDER
from ..classes.data import Args

VERSION = metadata.version("satori-ci")
just_fix_windows_console()

default_options = [
    click.option("-p", "--profile", default="default"),
    click.option("-j", "--json", is_flag=True, help="JSON output"),
    click.option("--debug", is_flag=True, help="Debug mode"),
    click.option("--timeout", type=int, default=180, help="Request timeout"),
    # click.option("--version", "-v", action="version", version=f"%(prog)s {VERSION}")
]


def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


@tui()
@click.group()
@add_options(default_options)
def main(**kargs):
    pass


@click.command
@click.argument("key")
@click.argument("value")
def config(key, value, **kargs):
    instance = Satori(Args(**kargs), config=True)
    instance.save_config(key, value)


@click.command
@add_options(default_options)
def dashboard(**kargs):
    args = Args(**kargs)
    instance = Satori(args, config=True)
    instance.dashboard(args)


@click.command
@click.argument("path")
@click.option("-s", "--sync", default=False, is_flag=True)
@click.option("-o", "--output", default=False, is_flag=True)
@click.option("-r", "--report", default=False, is_flag=True)
@click.option("-d", "--data", type=str, default="", help="Secrets")
@add_options(default_options)
def run(**kargs):
    args = Args(**kargs)
    instance = Satori(args)
    instance.run(args)


@click.command
@click.argument("id")
@click.argument("action", type=click.Choice(["", "delete"]))
@click.option("-n", "--page", type=int, default=1, help="Playbooks page number")
@click.option("-l", "--limit", type=int, default=5, help="Page limit number")
@click.option("--public", is_flag=True, help="Fetch public satori playbooks")
@add_options(default_options)
def playbook(**kargs):
    args = Args(**kargs)
    instance = Satori(args)
    instance.playbook(args)


@click.command
@click.argument("id")
@click.argument(
    "action",
    type=click.Choice(
        [
            "",
            "commits",
            "commits",
            "check-commits",
            "check-forks",
            "scan",
            "scan-stop",
            "run",
            "clean",
        ]
    ),
)
@click.option("-c", "--coverage", type=float, default=1, help="coverage")
@click.option("--skip-check", default=False, is_flag=True)
@click.option("-f", "--from", type=str, default="", help="From Date")
@click.option("-t", "--to", type=str, default="", help="To Date")
@click.option("--delete-commits", default=False, is_flag=True)
@click.option("-s", "--sync", default=False, is_flag=True)
@click.option("-d", "--data", type=str, default="", help="Secrets")
@click.option("-b", "--branch", type=str, default="main", help="Repo branch")
@click.option("--filter", type=str, help="Filter names")
@click.option("-a", "--all", default=False, is_flag=True)
@click.option("-l", "--limit", type=int, default=100, help="Limit number")
@click.option("--fail", default=False, is_flag=True)
@click.option("--playbook", type=str, help="Playbook")
@add_options(default_options)
def repo(**kargs):
    args = Args(**kargs)
    instance = Satori(args)
    instance.repo(args)


@click.command
@click.argument("id")
@click.argument("action", type=click.Choice(["", "output", "stop", "delete"]))
@click.option("-n", "--page", type=int, default=1, help="Commit page number")
@click.option("-l", "--limit", type=int, default=20, help="Page limit number")
@click.option(
    "-f",
    "--filter",
    type=str,
    default="",
    help="Filters: from,to,satori_error,status",
)
@add_options(default_options)
def report(**kargs):
    args = Args(**kargs)
    instance = Satori(args)
    instance.report(args)


@click.command
@click.argument("id")
@click.argument("action", type=click.Choice(["", "stop", "start", "delete"]))
@add_options(default_options)
def monitor(**kargs):
    args = Args(**kargs)
    instance = Satori(args)
    instance.monitor(args)


@click.command
@click.argument("id")
@click.argument(
    "action",
    type=click.Choice(["", "create", "members", "add_member", "repos", "add_repo"]),
)
@click.option("--email", type=str, help="User email")
@click.option("--role", type=str, default="READ", help="User role")
@click.option("--repo", type=str, default=None, help="Repo name")
@add_options(default_options)
def team(**kargs):
    args = Args(**kargs)
    instance = Satori(args)
    instance.team(args)


@click.command
@click.option("-w", "--web", default=False, is_flag=True)
@add_options(default_options)
def help(**kargs):
    args = Args(**kargs)
    instance = Satori(args)
    if args.web:
        handler = partial(SimpleHTTPRequestHandler, directory=DOCS_FOLDER)
        httpd = HTTPServer(("localhost", 9090), handler)
        console.print("Docs server running on: [link]http://localhost:9090")
        httpd.serve_forever()
    else:
        gui = HelpGui(instance)
        gui.run()


main.add_command(config)
main.add_command(dashboard)
main.add_command(run)
main.add_command(playbook)
main.add_command(repo)
main.add_command(report)
main.add_command(monitor)
if __name__ == "__main__":
    main()
