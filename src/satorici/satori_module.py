#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
from importlib import metadata

from requests import HTTPError, Response

from satorici.classes.satori import Satori

VERSION = metadata.version("satori-ci")

def main():
    print(f"Satori CI {VERSION} - Automated Software Testing Platform", file=sys.stderr)
    if not (sys.version_info.major == 3 and sys.version_info.minor >= 9):
        print(
            "Minimum Python version 3.9 required, the current version is "
            f"{sys.version_info.major}.{sys.version_info.minor}\n"
            "How To Install Python 3.10 on Ubuntu: "
            "https://computingforgeeks.com/how-to-install-python-on-ubuntu-linux-system/"
            )
        sys.exit(0)

    baseparser = argparse.ArgumentParser(add_help=False)
    baseparser.add_argument("-p", "--profile", default="default")

    parser = argparse.ArgumentParser(parents=[baseparser])
    subparsers = parser.add_subparsers(dest="subcommand")

    # config token "user_token"
    config_cmd = subparsers.add_parser("config", parents=[baseparser])
    config_cmd.add_argument("key")
    config_cmd.add_argument("value")

    # run playbook.yml
    run_cmd = subparsers.add_parser("run", parents=[baseparser])
    run_cmd.add_argument("playbook")

    # upload ./directory
    upload_cmd = subparsers.add_parser("upload", parents=[baseparser])
    upload_cmd.add_argument("directory")

    # playbooks
    playbooks_cmd = subparsers.add_parser("playbooks", parents=[baseparser])

    # status id
    status_cmd = subparsers.add_parser("status", parents=[baseparser])
    status_cmd.add_argument("id")

    # cron list|stop <report_uuid>|stopall
    cron_cmd = subparsers.add_parser("cron", parents=[baseparser])
    cron_cmd.add_argument("action")
    cron_cmd.add_argument("param", default='all', nargs='?')

    # scan <repo_url>
    scan_cmd = subparsers.add_parser("scan", parents=[baseparser])
    scan_cmd.add_argument("repo_url", help="Github repository")
    scan_cmd.add_argument('-c', '--coverage', dest='coverage', type=float, default=0, help="coverage")
    scan_cmd.add_argument('-s', '--skip-check', dest='skip_check', default=False, action=argparse.BooleanOptionalAction)
    scan_cmd.add_argument('-f', '--from', dest='from_date', type=str, default='', help="From Date")
    scan_cmd.add_argument('-t', '--to', dest='to_date', type=str, default='', help="To Date")

    # stop <repo_name|repo_url|repor_uuid|monitor_id>
    stop_cmd = subparsers.add_parser("stop", parents=[baseparser])
    stop_cmd.add_argument("id", nargs='?', type=str, default='all', help="Github repository/Report UUID/Monitor ID")

    # info <repo_name|repo_url>
    info_cmd = subparsers.add_parser("info", parents=[baseparser])
    info_cmd.add_argument("repo", type=str, help="Github repository")

    # ci
    info_cmd = subparsers.add_parser("ci", parents=[baseparser])

    # clean <repo_name|repo_url>
    clean_cmd = subparsers.add_parser("clean", parents=[baseparser])
    clean_cmd.add_argument("repo", help="Github repository")
    clean_cmd.add_argument('-d', '--delete-commits', dest='delete_commits', default=False, action=argparse.BooleanOptionalAction)

    # report <repo_name|repo_url>
    report_cmd = subparsers.add_parser("report", parents=[baseparser])
    report_cmd.add_argument("repo", help="Github repository or report UUID")
    report_cmd.add_argument('-n', '--page', dest='page', type=int, default=1, help="Commit page number")
    report_cmd.add_argument('-l', '--limit', dest='limit', type=int, default=20, help="Page limit number")
    report_cmd.add_argument('-f', '--filter', dest='filter', type=str, default='', help="Filters: from,to,satori_error,status")
    report_cmd.add_argument("--json", action="store_true", help="Show json report")

    # monitor
    monitor_cmd = subparsers.add_parser("monitor", parents=[baseparser])

    # output
    output_cmd = subparsers.add_parser("output", parents=[baseparser])
    output_cmd.add_argument("id", help="Github repository or report UUID")

    args = parser.parse_args()

    if args.subcommand == "config":
        instance = Satori(args.profile, config=True)
    else:
        instance = Satori(args.profile)

    try:
        if args.subcommand == "config":
            instance.save_config(args.key, args.value)
        elif args.subcommand == "run":
            instance.run(args.playbook)
        elif args.subcommand == "upload":
            instance.upload(args.directory)
        elif args.subcommand == "playbooks":
            instance.playbooks()
        elif args.subcommand == "status":
            instance.report_status(args.id)
        elif args.subcommand == "cron":
            instance.cron_action(args.action, args.param)
        elif args.subcommand == "scan":
            instance.scan(args.repo_url, args.coverage, args.skip_check, args.from_date, args.to_date)
        elif args.subcommand == "stop":
            instance.stop(args.id)
        elif args.subcommand == "info":
            instance.scan_info(args.repo)
        elif args.subcommand == "ci":
            instance.ci()
        elif args.subcommand == "clean":
            instance.clean(args.repo, args.delete_commits)
        elif args.subcommand == "report":
            instance.report_info(args.repo, args.page, args.limit, args.filter, args.json)
        elif args.subcommand == "monitor":
            instance.monitor()
        elif args.subcommand == "output":
            instance.output(args.id)
        elif not args.subcommand or args.subcommand == "dashboard":
            instance.dashboard()
    except HTTPError as e:
        res: Response = e.response
        print(f"Status code: {res.status_code}")
        print(f"Body: {res.json()}")


if __name__ == "__main__":
    main()
