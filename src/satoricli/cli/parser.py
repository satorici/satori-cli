#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
import subprocess
import sys
import requests  # autoupgrade
from importlib import metadata
from rich import print
from pkg_resources import get_distribution, DistributionNotFound  # autoupgrade
from packaging import version  # autoupgrade
from datetime import date, datetime

# from subprocess import call # autoupgrade
from ..classes.satori import Satori
from ..classes.utils import console

VERSION = metadata.version("satori-ci")


def add_satori_arguments(cmd: ArgumentParser):
    # satori-cli repo|report|monitor|... {id} {action} ...
    cmd.add_argument("id", nargs="?", default="", help="Object ID")
    cmd.add_argument("action", nargs="?", default="", help="Action to perform")


def upgrade():
    """Verify the current version and the latest version"""
    upgrade_required = ""

    # Name of your package
    package_names = ["satori-ci", "satori-playbook-validator", "satori-docs"]

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
        print(
            (
                "[yellow]WARNING:[/] Newer version found, upgrade with: "
                f"[b]pip3 install -U {upgrade_required}"
            ),
            file=sys.stderr,
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
    run_cmd.add_argument("-s", "--sync", action="store_true")
    run_cmd.add_argument("-o", "--output", action="store_true")
    run_cmd.add_argument("-r", "--report", action="store_true")
    run_cmd.add_argument("-f", "--files", action="store_true")
    run_cmd.add_argument("-d", "--data", default="", help="Secrets")

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
    repo_cmd.add_argument("--skip-check", action="store_true")
    repo_cmd.add_argument("-f", "--from", default="", help="From Date")
    repo_cmd.add_argument("-t", "--to", dest="to", default="", help="To Date")
    repo_cmd.add_argument("--delete-commits", action="store_true")
    repo_cmd.add_argument("-s", "--sync", action="store_true")
    repo_cmd.add_argument("-d", "--data", default="", help="Secrets")
    repo_cmd.add_argument("-b", "--branch", default="main", help="Repo branch")
    repo_cmd.add_argument("--filter", help="Filter names")
    repo_cmd.add_argument("-a", "--all", action="store_true")
    repo_cmd.add_argument("-l", "--limit", type=int, default=100, help="Limit number")
    repo_cmd.add_argument("--fail", action="store_true")
    repo_cmd.add_argument("--playbook", help="Playbook")
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
        default="",
        help="Filters: from,to,satori_error,status",
    )
    add_satori_arguments(report_cmd)

    # outputs
    outputs_cmd = subparsers.add_parser("outputs", parents=[baseparser])
    outputs_cmd.add_argument(
        "--raw", action="store_true", help="Print without formatting"
    )
    output_filters = outputs_cmd.add_argument_group("filters")
    output_filters.add_argument(
        "--from",
        type=date.fromisoformat,
        help="Date in ISO format",
        metavar="DATE",
        dest="from_date",
    )
    output_filters.add_argument(
        "--to",
        type=date.fromisoformat,
        help="Date in ISO format",
        metavar="DATE",
        dest="to_date",
    )
    output_filters.add_argument("-n", "--name", help="Playbook name")
    output_filters.add_argument(
        "-f",
        "--failed",
        action="store_const",
        const=True,
        help="Fetch only failed reports outputs",
    )

    # monitor {id} <start|stop|delete>
    monitor_cmd = subparsers.add_parser("monitor", parents=[baseparser])
    monitor_cmd.add_argument(
        "--clean", action="store_true", help="Clean all report related"
    )
    monitor_cmd.add_argument(
        "--deleted", action="store_true", help="Display deleted monitors"
    )
    add_satori_arguments(monitor_cmd)

    # team {id} create|members|delete|add_member|repos|
    # add_repo|get_token|refresh_token|del_member
    team_cmd = subparsers.add_parser("team", parents=[baseparser])
    team_cmd.add_argument("--email", help="User email")
    team_cmd.add_argument("--role", default="READ", help="User role")
    team_cmd.add_argument("--repo", default=None, help="Repo name")
    add_satori_arguments(team_cmd)
    # Add config args
    team_cmd.add_argument("config_name", nargs="?", default="")
    team_cmd.add_argument("config_value", nargs="?", default="")

    # help
    help_cmd = subparsers.add_parser("help", parents=[baseparser])
    help_cmd.add_argument("-w", "--web", action="store_true")
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
                subprocess.run(["satori-docs", "--web"])
            else:
                subprocess.run(["satori-docs"])
        elif args.subcommand == "outputs":
            instance.get_outputs(**vars(args))
    except KeyboardInterrupt:
        console.print("[critical]Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
