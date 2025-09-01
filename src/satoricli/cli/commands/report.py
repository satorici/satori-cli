import re
from argparse import ArgumentParser
from typing import Literal, get_args

from rich.syntax import Syntax
from rich.table import Table

from satoricli.api import client
from satoricli.cli.utils import (
    add_table_row,
    autoformat,
    autosyntax,
    console,
    date_formatter,
    download_files,
    error_console,
    execution_time,
    get_command_params,
    print_output,
    wait,
)

from .base import BaseCommand

VISIBILITY_VALUES = ("public", "private", "unlisted")
ACTIONS = Literal[
    "show",
    "output",
    "stop",
    "files",
    "delete",
    "status",
    "set-team",
    "visibility",
]


class ReportCommand(BaseCommand):
    name = "report"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id", metavar="ID")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=get_args(ACTIONS),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument("action2", nargs="?", default=None)
        parser.add_argument(
            "--test",
            dest="filter_tests",
            help="Print specified test output",
            action="append",
            default=[],
        )
        parser.add_argument(
            "--format",
            dest="text_format",
            help="Format text output (Plain or Markdown text)",
            default="plain",
            choices=("plain", "md"),
        )

    def __call__(
        self,
        id: str,
        action: ACTIONS,
        action2: str,
        filter_tests: list,
        text_format: Literal["plain", "md"],
        **kwargs,
    ):
        if action == "show":
            res = client.get(f"/reports/{id}").json()
            if kwargs["json"]:
                autoformat(res, jsonfmt=kwargs["json"])
            else:
                ReportCommand.print_report_single(res)
        elif action == "output":
            status = client.get(f"/reports/{id}/status").text

            if status == "Running":
                wait(id, True)
            else:
                print_output(id, kwargs["json"], filter_tests, text_format)
        elif action == "files":
            download_files(id)
        elif action == "stop":
            res = client.get(f"/reports/{id}/stop").json()
            autoformat(res, jsonfmt=kwargs["json"])
        elif action == "delete":
            client.delete(f"/reports/{id}")
            console.print("Report deleted")
        elif action == "visibility":
            if not action2 or action2 not in VISIBILITY_VALUES:
                error_console.print(
                    f"Allowed values for visibility: {VISIBILITY_VALUES}",
                )
                return 1
            res = client.patch(
                f"/reports/{id}", json={"visibility": action2.capitalize()},
            ).json()
            autoformat(res)
        elif action == "status":
            res = client.get(f"/reports/{id}/status").text
            autoformat(res)
        elif action == "set-team":
            res = client.patch(
                f"/reports/{id}/team", params={"team_name": action2},
            ).json()
            autoformat(res)
        return 0

    @staticmethod
    def print_report_list(report_list: list) -> None:
        """Print reports list as a table.

        Parameters
        ----------
        report_list : list
            Reports list

        """
        for report in report_list:
            table = Table(
                show_header=False, show_lines=True, highlight=True, expand=True
            )
            add_table_row(
                [
                    ["ID", report["id"]],
                    ["Team", report["team"], "cyan1"],
                    ["Playbook name", report["playbook_name"], "cyan1"],
                    ["Report URL", report.get("report_url"), "blue"],
                ],
                table,
            )
            add_table_row(
                [
                    ["Execution type", report["execution"], "bright_magenta"],
                    ["Visibility", report["visibility"]],
                    ["Runtime", execution_time(report.get("execution_time"))],
                    ["User", report["user"]],
                    ["Date", date_formatter(report["date"])],
                    ["Status", report["status"]],
                    ["Result", report["result"]],
                ],
                table,
            )

            if report.get("repo"):
                add_table_row(
                    [
                        ["Repo", report["repo"]],
                        ["Branch", report["branches"]],
                        ["Hash", report["hash"]],
                        ["Commit author", report["commit_author"]],
                    ],
                    table,
                )

            # Playbooks Line
            playbook_line = []
            if report["playbook_path"]:
                playbook_line.append(["Path", report["playbook_path"]])
            if report["secrets_count"]:
                playbook_line.append(["Parameters", report["secrets_count"]])
            if playbook_line:
                add_table_row(playbook_line, table)

            if report["testcases"]:
                tests = ""
                for test in report["testcases"]:
                    style = "[pass]" if re.search(r"pass$", test) else "[fail]"
                    tests += f"\n  ○ {style}{test}"
                table.add_row(f"[b]Testcases:[/]{tests}")
            if report["errors"]:
                table.add_row(
                    "[warning]Warnings and Errors:[/]\n ○ "
                    + str(report["errors"]).replace("\n", "\n ○ ")
                )
            console.print(table, "\n")

    @staticmethod
    def print_report_single(report: dict):
        """Print a single report as a table.

        Parameters
        ----------
        report : dict
            Report data
        """
        table = Table(show_header=False, show_lines=True, highlight=True, expand=True)
        # Create a row with the basic info
        add_table_row(
            [
                ["ID", report["id"]],
                ["Team", report["team"], "cyan1"],
                ["Playbook name", report["name"], "cyan1"],
                ["Report url", report.get("report_url"), "blue"],
            ],
            table,
        )
        # Add another row with the report data
        add_table_row(
            [
                ["Execution type", report["execution"], "bright_magenta"],
                ["Visibility", report["visibility"]],
                ["Source", report["source"]],
                ["Runtime", execution_time(report.get("execution_time"))],
                ["Monitor", report["monitor_id"]],
                ["Date", date_formatter(report["created"])],
                ["Status", report["status"]],
                ["Result", report["result"]],
            ],
            table,
        )

        if report.get("repo"):
            # Add the repo data in another row if exist
            add_table_row(
                [
                    ["Repo", report["repo"]],
                    ["Branch", report["branches"]],
                    ["Hash", report["hash"]],
                    ["Parent", report.get("parent_hash")],
                ],
                table,
            )

        # Add the playbook data in a new row
        playbook_line = []
        if report["playbook_path"]:
            playbook_line.append(["Path", report["playbook_path"]])
        if report["secrets_count"]:
            playbook_line.append(["Secrets Count", report["secrets_count"]])
        params = get_command_params(report["run_params"])
        if params:
            playbook_line.append(["Parameters", params])
        if len(playbook_line) > 0:
            add_table_row(playbook_line, table)

        # Highlight the playbook content
        playbook_content = autosyntax(report["playbook"], echo=False)
        if isinstance(playbook_content, Syntax):
            table.add_row(playbook_content)
        if report["testcases"]:
            tests = ""
            for test in report["testcases"]:
                style = "[pass]" if re.search(r"pass$", test) else "[fail]"
                tests += f"\n  ○ {style}{test}"
            table.add_row(f"[b]Testcases:[/]{tests}")
        if report["report"]:
            ReportCommand.print_report_summary(report["report"], table)
        if report["delta"]:
            table.add_row(f"[b]Report:[/]\n{autoformat(report['delta'], echo=False)}")
        if report["user_warnings"]:
            table.add_row(
                "[warning]Warnings and Errors:[/]\n ○ "
                + str(report["user_warnings"]).replace("\n", "\n ○ ")
            )
        console.print(table)  # Print the table content

    @staticmethod
    def print_report_summary(report_data: list, table: Table):
        """Print the json content of a report.

        Parameters
        ----------
        report_data : list
            Report json
        table : Table
            Table to add the content
        """
        for report in report_data:
            if not report["asserts"]:
                continue
            assert_props = [
                ["Test", report["test"]],
            ]
            if report.get("severity"):
                assert_props.append(["Severity", report["severity"]])
            test_status = (
                report["test_status"]
                if not report["total_fails"]
                else f"Fail({report['total_fails']})"
            )
            assert_props.extend([["Test status", test_status]])
            row = add_table_row(assert_props, table, echo=False) or ""
            for ast in report["asserts"]:
                assert_status = (
                    ast["status"] if not ast["count"] else f"Fail({ast['count']})"
                )
                row += "\n" + (
                    add_table_row(
                        [
                            ["Assert", ast["assert"]],
                            [
                                "Assert Value",
                                ast["expected"].strip()
                                if isinstance(ast["expected"], str)
                                else "",
                            ],
                            ["Status", assert_status],
                        ],
                        table,
                        echo=False,
                    )
                    or ""
                )
            table.add_row(row)

    @staticmethod
    def print_report_asrt(report_id: str, json_out: bool):
        """Fetch the report and print the report summary.

        Parameters
        ----------
        report_id : str
            ID of the report
        json_out : bool
            Print as json?
        """
        # Fetch the report data
        report_data = client.get(f"/reports/{report_id}").json()
        json_data = report_data.get("report")
        if json_data:
            if json_out:  # Print as json if --json is defined
                console.print_json(data=json_data)
            else:
                table = Table(
                    show_header=False, show_lines=True, highlight=True, expand=True
                )
                add_table_row(
                    [["Result", report_data["result"]]],
                    table,
                )

                # Add the parameters if they exist
                params = get_command_params(report_data["run_params"])
                if params:
                    add_table_row([["Parameters", params]], table)

                ReportCommand.print_report_summary(report_data["report"], table)
                console.print(table)
        elif report_data["status"] == "Timeout":
            console.print("[error]Report timed out")
        else:
            console.print("[error]Report not found")
