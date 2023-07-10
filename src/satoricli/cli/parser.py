#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
import sys
import requests  # autoupgrade
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from importlib import metadata
from colorama import just_fix_windows_console
from rich import print
from pkg_resources import get_distribution, DistributionNotFound  # autoupgrade
from packaging import version  # autoupgrade
from datetime import datetime

# from subprocess import call # autoupgrade
from ..classes.satori import Satori
from ..classes.utils import console
from ..classes.help_gui import HelpGui, DOCS_FOLDER

VERSION = metadata.version("satori-ci")
just_fix_windows_console()


def add_satori_arguments(cmd: ArgumentParser):
    # satori-cli repo|report|monitor|... {id} {action} ...
    cmd.add_argument("id", nargs="?", type=str, default="", help="Object ID")
    cmd.add_argument(
        "action", nargs="?", type=str, default="", help="Action to perform"
    )


def upgrade():
    """Verify the current version and the latest version"""
    upgrade_required = ""

    # Name of your package
    package_names = ["satori-ci", "satori-playbook-validator"]

    for package_name in package_names:
        # Get the current version
        try:
            current_version = get_distribution(package_name).version
        except DistributionNotFound:
            print(f"{package_name} is not installed.")
            current_version = None

        # Get the latest version
        latest_version = None
        response = requests.get(
            f"https://pypi.org/pypi/{package_name}/json", timeout=10
        )
        if response.status_code == 200:
            latest_version = response.json()["info"]["version"]
        else:
            print(f"Unable to get the latest version of the package ${package_name}.")

        # Compare the versions and upgrade if necessary
        if (
            current_version
            and latest_version
            and version.parse(current_version) < version.parse(latest_version)
        ):
            upgrade_required += package_name + " "
    if upgrade_required:
        console.print(
            "[warning]WARNING:[/] Newer version found, upgrade with: "
            "[b]pip install -U " + upgrade_required
        )


def main():
    timestamp = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"[dim]Satori CI {VERSION} - Automated Software Testing Platform - Started on {timestamp}",
        file=sys.stderr,
    )
    if not (sys.version_info.major == 3 and sys.version_info.minor >= 9):
        console.print(
            "[danger]Minimum Python version 3.9 required, the current version is "
            f"{sys.version_info.major}.{sys.version_info.minor}[/]\n"
            "How To Install Python 3.10 on Ubuntu:\n"
            "[link]https://computingforgeeks.com/how-to-install-python-on-ubuntu-linux-system"
        )
        sys.exit(0)

    upgrade()

    baseparser = ArgumentParser(add_help=False)
    baseparser.add_argument("-p", "--profile", default="default")
    baseparser.add_argument("-j", "--json", action="store_true", help="JSON output")
    baseparser.add_argument("--debug", action="store_true", help="Debug mode")
    baseparser.add_argument("--timeout", type=int, default=180, help="Request timeout")
    baseparser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {VERSION}"
    )

    parser = ArgumentParser(parents=[baseparser], prog="satori-cli")
    subparsers = parser.add_subparsers(dest="subcommand")

    # config token "user_token"
    config_cmd = subparsers.add_parser("config", parents=[baseparser])
    config_cmd.add_argument("key")
    config_cmd.add_argument("value")

    # dashboard
    subparsers.add_parser("dashboard", parents=[baseparser])

    # run playbook.yml
    run_cmd = subparsers.add_parser("run", parents=[baseparser])
    run_cmd.add_argument("path")
    run_cmd.add_argument("-s", "--sync", default=False, action="store_true")
    run_cmd.add_argument("-o", "--output", default=False, action="store_true")
    run_cmd.add_argument("-r", "--report", default=False, action="store_true")
    run_cmd.add_argument("-f", "--files", default=False, action="store_true")
    run_cmd.add_argument("-d", "--data", type=str, default="", help="Secrets")

    # playbook {id} <delete>
    playbook_cmd = subparsers.add_parser("playbook", parents=[baseparser])
    playbook_cmd.add_argument(
        "-n", "--page", dest="page", type=int, default=1, help="Playbooks page number"
    )
    playbook_cmd.add_argument(
        "-l", "--limit", dest="limit", type=int, default=5, help="Page limit number"
    )
    playbook_cmd.add_argument(
        "--public", action="store_true", help="Fetch public satori playbooks"
    )
    add_satori_arguments(playbook_cmd)

    # repo {id} <commits|check-commits|check-forks|scan|scan-stop|run|clean>
    repo_cmd = subparsers.add_parser("repo", parents=[baseparser])
    repo_cmd.add_argument("-c", "--coverage", type=float, default=1, help="coverage")
    repo_cmd.add_argument("--skip-check", default=False, action="store_true")
    repo_cmd.add_argument("-f", "--from", type=str, default="", help="From Date")
    repo_cmd.add_argument("-t", "--to", dest="to", type=str, default="", help="To Date")
    repo_cmd.add_argument("--delete-commits", default=False, action="store_true")
    repo_cmd.add_argument("-s", "--sync", default=False, action="store_true")
    repo_cmd.add_argument("-d", "--data", type=str, default="", help="Secrets")
    repo_cmd.add_argument(
        "-b", "--branch", type=str, default="main", help="Repo branch"
    )
    repo_cmd.add_argument("--filter", type=str, help="Filter names")
    repo_cmd.add_argument("-a", "--all", default=False, action="store_true")
    repo_cmd.add_argument("-l", "--limit", type=int, default=100, help="Limit number")
    repo_cmd.add_argument("--fail", default=False, action="store_true")
    repo_cmd.add_argument("--playbook", type=str, help="Playbook")
    add_satori_arguments(repo_cmd)

    # report {id} <output|stop|delete>
    report_cmd = subparsers.add_parser("report", parents=[baseparser])
    report_cmd.add_argument(
        "-n", "--page", type=int, default=1, help="Commit page number"
    )
    report_cmd.add_argument(
        "-l", "--limit", type=int, default=20, help="Page limit number"
    )
    report_cmd.add_argument(
        "-f",
        "--filter",
        type=str,
        default="",
        help="Filters: from,to,satori_error,status",
    )
    add_satori_arguments(report_cmd)

    # monitor {id} <start|stop|delete>
    monitor_cmd = subparsers.add_parser("monitor", parents=[baseparser])
    monitor_cmd.add_argument(
        "--clean", default=False, action="store_true", help="Clean all report related"
    )
    monitor_cmd.add_argument(
        "--deleted", default=False, action="store_true", help="Display deleted monitors"
    )
    add_satori_arguments(monitor_cmd)

    # team {id} create|members|add_member|repos|
    # add_repo|get_token|refresh_token|del_member
    team_cmd = subparsers.add_parser("team", parents=[baseparser])
    team_cmd.add_argument("--email", type=str, help="User email")
    team_cmd.add_argument("--role", type=str, default="READ", help="User role")
    team_cmd.add_argument("--repo", type=str, default=None, help="Repo name")
    add_satori_arguments(team_cmd)
    # Add config args
    team_cmd.add_argument("config_name", nargs="?", type=str, default="")
    team_cmd.add_argument("config_value", nargs="?", type=str, default="")

    # help
    help_cmd = subparsers.add_parser("help", parents=[baseparser])
    help_cmd.add_argument("-w", "--web", default=False, action="store_true")
    add_satori_arguments(help_cmd)

    # user {id} TODO: <delete|disable|enable?>
    user_cmd = subparsers.add_parser("user", parents=[baseparser])
    add_satori_arguments(user_cmd)

    args = parser.parse_args()

    if args.subcommand == "config":
        instance = Satori(args, config=True)
    else:
        instance = Satori(args)

    try:
        if args.subcommand == "config":
            instance.save_config(args.key, args.value)
        elif args.subcommand == "run":
            instance.run(args)
        elif args.subcommand == "playbook":
            instance.playbook(args)
        elif args.subcommand == "repo":
            instance.repo(args)
        elif args.subcommand == "report":
            instance.report(args)
        elif args.subcommand == "monitor":
            instance.monitor(args)
        elif args.subcommand == "team":
            instance.team(args)
        elif args.subcommand == "user":
            instance.user(args)
        elif args.subcommand in (None, "dashboard"):
            instance.dashboard(args)
        elif args.subcommand == "help":
            if args.web:
                handler = partial(SimpleHTTPRequestHandler, directory=DOCS_FOLDER)
                httpd = HTTPServer(("localhost", 9090), handler)
                console.print("Docs server running on: [link]http://localhost:9090")
                httpd.serve_forever()
            else:
                gui = HelpGui(instance)
                gui.run()
    except KeyboardInterrupt:
        console.print("[critical]Interrupted by user")
        sys.exit(1)
