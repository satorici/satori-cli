#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import sys
from importlib import metadata

from satorici.classes.satori import Satori

VERSION = metadata.version("satori-ci")

def main():
    print(f"Satori CI {VERSION} - Automated Software Testing Platform")
    if not (sys.version_info.major == 3 and sys.version_info.minor >= 9):
        print(f"Minimum Python version 3.9 required, the current version is {sys.version_info.major}.{sys.version_info.minor}\nHow To Install Python 3.10 on Ubuntu: https://computingforgeeks.com/how-to-install-python-on-ubuntu-linux-system/")
        sys.exit(0)

    parser = argparse.ArgumentParser(add_help=True, exit_on_error=True)

    sub_parsers = parser.add_subparsers(dest="subcommand")

    base_subparser = argparse.ArgumentParser(add_help=False)
    # Shared params
    base_subparser.add_argument("-p", "--profile", default="default")

    # config token "user_token"
    config_cmd = sub_parsers.add_parser("config", parents=[base_subparser])
    config_cmd.add_argument("key")
    config_cmd.add_argument("value")

    # run playbook.yml
    run_cmd = sub_parsers.add_parser("run", parents=[base_subparser])
    run_cmd.add_argument("playbook")

    # upload ./directory
    upload_cmd = sub_parsers.add_parser("upload", parents=[base_subparser])
    upload_cmd.add_argument("directory")

    # playbooks
    playbooks_cmd = sub_parsers.add_parser("playbooks", parents=[base_subparser])

    # status id
    status_cmd = sub_parsers.add_parser("status", parents=[base_subparser])
    status_cmd.add_argument("id")

    # cron list|stop <report_uuid>|stopall
    cron_cmd = sub_parsers.add_parser("cron", parents=[base_subparser])
    cron_cmd.add_argument("action")
    cron_cmd.add_argument("param", default='all', nargs='?')

    # scan <repo_url>
    scan_cmd = sub_parsers.add_parser("scan", parents=[base_subparser])
    scan_cmd.add_argument("repo_url", help="Github repository")
    scan_cmd.add_argument('-c', '--coverage', dest='coverage', type=float, default=0, help="coverage")
    scan_cmd.add_argument('-s', '--skip-check', dest='skip_check', default=False, action=argparse.BooleanOptionalAction)
    scan_cmd.add_argument('-f', '--from', dest='from_date', type=str, default='', help="From Date")
    scan_cmd.add_argument('-t', '--to', dest='to_date', type=str, default='', help="To Date")

    # stop <repo_name|repo_url|repor_uuid|monitor_id>
    stop_cmd = sub_parsers.add_parser("stop", parents=[base_subparser])
    stop_cmd.add_argument("id", nargs='?', type=str, default='all', help="Github repository/Report UUID/Monitor ID")

    # info <repo_name|repo_url>
    info_cmd = sub_parsers.add_parser("info", parents=[base_subparser])
    info_cmd.add_argument("repo", type=str, help="Github repository")

    # ci
    info_cmd = sub_parsers.add_parser("ci", parents=[base_subparser])

    # clean <repo_name|repo_url>
    clean_cmd = sub_parsers.add_parser("clean", parents=[base_subparser])
    clean_cmd.add_argument("repo", help="Github repository")
    clean_cmd.add_argument('-d', '--delete-commits', dest='delete_commits', default=False, action=argparse.BooleanOptionalAction)

    # report <repo_name|repo_url>
    report_cmd = sub_parsers.add_parser("report", parents=[base_subparser])
    report_cmd.add_argument("repo", help="Github repository or report UUID")
    report_cmd.add_argument('-n', '--page', dest='page', type=int, default=1, help="Commit page number")
    report_cmd.add_argument('-l', '--limit', dest='limit', type=int, default=20, help="Page limit number")
    report_cmd.add_argument('-f', '--filter', dest='filter', type=str, default='', help="Filters: from,to,satori_error,status")

    # monitor
    monitor_cmd = sub_parsers.add_parser("monitor", parents=[base_subparser])

    # output
    output_cmd = sub_parsers.add_parser("output", parents=[base_subparser])
    output_cmd.add_argument("id", help="Github repository or report UUID")

    argv_len = len(sys.argv)
    if argv_len <= 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.subcommand == "config":
        instance = Satori(args.profile, config=True)
    else:
        instance = Satori(args.profile)

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
        instance.report_info(args.repo, args.page, args.limit, args.filter)
    elif args.subcommand == "monitor":
        instance.monitor()
    elif args.subcommand == "output":
        instance.output(args.id)


if __name__ == "__main__":
    main()
