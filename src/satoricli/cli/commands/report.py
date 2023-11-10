from argparse import ArgumentParser
import re
from typing import Literal, Optional
from rich.table import Table
from rich.syntax import Syntax

from satoricli.api import client
from satoricli.cli.utils import (
    autoformat,
    console,
    download_files,
    print_output,
    autosyntax,
    add_table_row,
)

from .base import BaseCommand


class ReportCommand(BaseCommand):
    name = "report"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("id", metavar="ID")
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=("show", "output", "stop", "files", "delete", "public"),
            nargs="?",
            default="show",
            help="action to perform",
        )

    def __call__(
        self,
        id: str,
        action: Literal["show", "output", "stop", "files", "delete", "public"],
        **kwargs,
    ):
        if action == "show":
            res = client.get(
                f"/reports/{id or ''}",
                params={"page": page, "limit": limit, "filter": filter},
            ).json()

            if not id and not kwargs["json"]:
                if res["count"] == 0:
                    console.print("No reports found")
                    return

                ReportCommand.print_report_list(res["list"])
            elif kwargs["json"]:
                autoformat(res, jsonfmt=kwargs["json"])
            else:  # single report
                ReportCommand.print_report_single(res)
        elif action == "output":
            print_output(id, print_json=kwargs["json"])
        elif action == "files":
            download_files(id)
        elif action == "stop":
            res = client.get(f"/reports/{id}/stop").json()
            autoformat(res, jsonfmt=kwargs["json"])
        elif action == "delete":
            client.delete(f"/reports/{id}")
            print("Report deleted")
        elif action == "public":
            res = client.patch(f"/reports/{id}", json={"public": "invert"}).json()
            autoformat(res)

    @staticmethod
    def print_report_list(report_list: list):
        """Print reports list as a table

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
                    ["Team", report["team"]],
                    ["Playbook name", report["playbook_name"]],
                ],
                table,
            )
            add_table_row(
                [
                    ["Execution type", report["execution"]],
                    ["Public", report["public"]],
                    ["Time required", report["time required"]],
                    ["User", report["user"]],
                    ["Date", report["date"].replace("T", " ")],
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
            add_table_row(
                [
                    ["Playbook", report["playbook_id"]],
                    ["Url", report["playbook_url"]],
                ],
                table,
            )
            if report["testcases"]:
                tests = ""
                for test in report["testcases"]:
                    style = "[pass]" if re.search(r"pass$", test) else "[fail]"
                    tests += f"\n  ○ {style}{test}"
                table.add_row(f"[b]Testcases:[/]{tests}")
            console.print(table)

    @staticmethod
    def print_report_single(report: dict):
        """Print a single report as a table

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
                ["Team", report["team"]],
                ["Playbook name", report["name"]],
            ],
            table,
        )
        # Add another row with the report data
        add_table_row(
            [
                ["Execution type", report["execution"]],
                ["Public", report["public"]],
                ["Source", report["source"]],
                ["Time required", report["time_required"]],
                ["Monitor", report["monitor_id"]],
                ["Date", report["created"].replace("T", " ")],
                ["Fails", report["fails"]],
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
                    ["Parent", report["parent_hash"]],
                ],
                table,
            )
        # Add the playbook data in a new row
        add_table_row(
            [
                ["Playbook", report["playbook_id"]],
                ["Url", report["playbook_url"]],
            ],
            table,
        )
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
            table.add_row(f"[b]Report:[/]\n{autoformat(report['delta'],echo=False)}")
        console.print(table) # Print the table content

    @staticmethod
    def print_report_summary(report_data: list, table: Table):
        """Print the json content of a report

        Parameters
        ----------
        report_data : list
            Report json
        table : Table
            Table to add the content
        """
        for report in report_data:
            assert_props = [
                ["Test", report["test"]],
            ]
            if report["severity"]:
                assert_props.append(report["severity"])
            assert_props.extend(
                [
                    ["Testcases", report["testcases"]],
                    ["Test status", report["test_status"]],
                    ["Total Fails", report["total_fails"]],
                ]
            )
            row = add_table_row(assert_props, table, echo=False) or ""
            for ast in report["asserts"]:
                row += "\n" + (
                    add_table_row(
                        [
                            ["Assert", ast["assert"]],
                            ["Count", ast["count"]],
                            ["Expected", ast["expected"]],
                            ["Status", ast["status"]],
                        ],
                        table,
                        echo=False,
                    )
                    or ""
                )
            table.add_row(row)

    @staticmethod
    def print_report_asrt(report_id: str, json_out: bool):
        """Fetch the report and print the report summary

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
        if json_out: # Print as json if --json is defined 
            console.print_json(data=json_data)
        else:
            table = Table(
                show_header=False, show_lines=True, highlight=True, expand=True
            )
            add_table_row(
                [
                    ["Fails", report_data["fails"]],
                    ["Result", report_data["result"]],
                ],
                table,
            )
            ReportCommand.print_report_summary(report_data["report"], table)
            console.print(table)
