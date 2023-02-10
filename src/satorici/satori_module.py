#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
from importlib import metadata

from requests import HTTPError, Response

from satorici.classes.satori import Satori
from satorici.classes.utils import autoformat

VERSION = metadata.version("satori-ci")


def add_satori_arguments(cmd):
    # satori-cli repo|report|monitor|... {id} {action} ...
    cmd.add_argument("id", nargs="?", type=str, default="list")
    cmd.add_argument("action", nargs="?", type=str, default="get")


def main():
    print(f"Satori CI {VERSION} - Automated Software Testing Platform", file=sys.stderr)
    if not (sys.version_info.major == 3 and sys.version_info.minor >= 9):
        print(
            "Minimum Python version 3.9 required, the current version is "
            f"{sys.version_info.major}.{sys.version_info.minor}\n"
            "How To Install Python 3.10 on Ubuntu: "
            "https://computingforgeeks.com/how-to-install-python-on-ubuntu-linux-system"
        )
        sys.exit(0)

    baseparser = argparse.ArgumentParser(add_help=False)
    baseparser.add_argument("-p", "--profile", default="default")
    baseparser.add_argument("-j", "--json", action="store_true", help="JSON output")

    parser = argparse.ArgumentParser(parents=[baseparser])
    subparsers = parser.add_subparsers(dest="subcommand")

    # config token "user_token"
    config_cmd = subparsers.add_parser("config", parents=[baseparser])
    config_cmd.add_argument("key")
    config_cmd.add_argument("value")

    # run playbook.yml
    run_cmd = subparsers.add_parser("run", parents=[baseparser])
    run_cmd.add_argument("path")
    run_cmd.add_argument("-s", "--sync", default=False, action="store_true")

    # playbook {id} <delete>
    playbook_cmd = subparsers.add_parser("playbook", parents=[baseparser])
    playbook_cmd.add_argument(
        "-n", "--page", dest="page", type=int, default=1, help="Playbooks page number"
    )
    playbook_cmd.add_argument(
        "-l", "--limit", dest="limit", type=int, default=5, help="Page limit number"
    )
    add_satori_arguments(playbook_cmd)

    # repo {id} <commits|check-commits|check-forks|scan|scan-stop|run|clean>
    repo_cmd = subparsers.add_parser("repo", parents=[baseparser])
    repo_cmd.add_argument(
        "-c", "--coverage", dest="coverage", type=float, default=0, help="coverage"
    )
    repo_cmd.add_argument(
        "-s", "--skip-check", dest="skip_check", default=False, action="store_true"
    )
    repo_cmd.add_argument(
        "-f", "--from", dest="from", type=str, default="", help="From Date"
    )
    repo_cmd.add_argument("-t", "--to", dest="to", type=str, default="", help="To Date")
    repo_cmd.add_argument(
        "-d",
        "--delete-commits",
        dest="delete_commits",
        default=False,
        action="store_true",
    )
    add_satori_arguments(repo_cmd)

    # report {id} <output|stop|delete>
    report_cmd = subparsers.add_parser("report", parents=[baseparser])
    report_cmd.add_argument(
        "-n", "--page", dest="page", type=int, default=1, help="Commit page number"
    )
    report_cmd.add_argument(
        "-l", "--limit", dest="limit", type=int, default=20, help="Page limit number"
    )
    report_cmd.add_argument(
        "-f",
        "--filter",
        dest="filter",
        type=str,
        default="",
        help="Filters: from,to,satori_error,status",
    )
    add_satori_arguments(report_cmd)

    # monitor {id} <start|stop|delete>
    monitor_cmd = subparsers.add_parser("monitor", parents=[baseparser])  # noqa: F841
    add_satori_arguments(monitor_cmd)

    args = parser.parse_args()

    if args.subcommand == "config":
        instance = Satori(args.profile, config=True)
    else:
        instance = Satori(args.profile)

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
        elif not args.subcommand or args.subcommand == "dashboard":
            instance.dashboard(args)
    except HTTPError as e:
        res: Response = e.response
        status = {"Status code": res.status_code}
        status.update(res.json())
        if args.json:
            print(str(status))
        else:
            autoformat(status, capitalize=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
