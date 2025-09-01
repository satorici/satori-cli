import datetime
import io
import itertools
import os
import tarfile
import time
from argparse import ArgumentParser
from math import ceil
from typing import Literal, Optional, get_args

from rich.progress import Progress, SpinnerColumn, TextColumn

from satoricli.api import client, disable_error_raise
from satoricli.cli.utils import (
    autoformat,
    autotable,
    console,
    date_formatter,
    error_console,
    execution_time,
    get_command_params,
)

from .base import BaseCommand

REPORT_VISIBILITY = Literal["public-global", "public", "unlisted", "private"]
RESULTS = Literal["pass", "fail", "unknown"]
PLAYBOOK_TYPE = Literal["public", "private"]
STATUS_FILTERS = Literal[
    "provisioning", "pending", "running", "completed", "stopped", "timeout"
]


def capitalize(s: Optional[str]) -> Optional[str]:
    return s.capitalize() if s else s


class ReportsCommand(BaseCommand):
    name = "reports"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-p", "--page", type=int, default=1)
        parser.add_argument("-l", "--limit", type=int, default=20)
        parser.add_argument(
            "--public", action="store_true", help="Fetch public reports"
        )

        subparser = parser.add_subparsers(dest="action")

        show_parser = subparser.add_parser("show")
        show_parser.add_argument("-f", "--filter")

        search_parser = subparser.add_parser("search", aliases=["delete"])
        search_parser.add_argument("-n", "--name", help="Export folder name")
        search_parser.add_argument(
            "--playbook-type",
            choices=get_args(PLAYBOOK_TYPE),
            default=None,
            help="Filter by playbook type",
        )
        search_parser.add_argument(
            "--report-visibility",
            choices=get_args(REPORT_VISIBILITY),
            help="Filter by report visibility",
        )
        search_parser.add_argument(
            "--result",
            choices=get_args(RESULTS),
            help="Filter by report result",
        )
        search_parser.add_argument(
            "--query",
            type=str,
            help="Filter by output string (support regex)",
        )
        search_parser.add_argument("--monitor", type=str, help="Filter by monitor ID")
        search_parser.add_argument(
            "--download", action="store_true", help="Download reports outputs to files"
        )
        search_parser.add_argument("--playbook", type=str, help="Filter by playbook")
        search_parser.add_argument("--force", action="store_true", help="Force delete")
        search_parser.add_argument(
            "--status", choices=get_args(STATUS_FILTERS), help="Filter by status"
        )
        search_parser.add_argument(
            "--from",
            type=datetime.datetime.fromisoformat,
            help="Filter by from date",
            dest="from_date",
        )
        search_parser.add_argument(
            "--to",
            type=datetime.datetime.fromisoformat,
            help="Filter by to date",
            dest="to_date",
        )
        search_parser.add_argument(
            "--severity",
            type=int,
            help="Filter by output severity",
        )

    def __call__(
        self,
        action: Optional[str],
        page: int = 1,
        limit: int = 20,
        filter: Optional[str] = None,
        public: bool = False,
        name: Optional[str] = None,
        playbook_type: Optional[PLAYBOOK_TYPE] = None,
        report_visibility: Optional[REPORT_VISIBILITY] = None,
        result: Optional[RESULTS] = None,
        query: Optional[str] = None,
        monitor: Optional[str] = None,
        download: bool = False,
        playbook: Optional[str] = None,
        force: bool = False,
        status: Optional[STATUS_FILTERS] = None,
        from_date: Optional[datetime.datetime] = None,
        to_date: Optional[datetime.datetime] = None,
        severity: Optional[int] = None,
        **kwargs,
    ):
        if action in ("delete", "search"):
            params = {
                "playbook_type": capitalize(playbook_type),
                "report_visibility": "Public-Global"
                if report_visibility == "public-global"
                else capitalize(report_visibility),
                "result": capitalize(result),
                "query": query,
                "limit": 10,
                "page": 1,
                "monitor": monitor,
                "playbook": playbook,
                "status": capitalize(status),
                "from_date": from_date,
                "to_date": to_date,
                "severity": severity,
            }

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

        if action in ("show", None):
            url = "/reports/public" if public else "/reports"
            res = client.get(
                url, params={"page": page, "limit": limit, "filters": filter}
            ).json()

            if not kwargs["json"]:
                if not res["total"]:
                    console.print("No reports found")
                    return 1

                self.print_table(res["rows"])
                console.print(
                    f"Page {page} of {ceil(res['total'] / limit)} | Total: {res['total']}"
                )
            else:
                autoformat(res["rows"], jsonfmt=kwargs["json"])
        elif action == "search":
            if not download:
                params["limit"] = limit
                params["page"] = page
                res = client.get("/reports/search", params=params).json()
                self.print_table(res["rows"])
                console.print(
                    f"Page {page} of {ceil(res['total'] / limit)} | Total: {res['total']}"
                )
                return 0

            # Save response
            extract_dir = name if name else "export"

            # Create directory if dont exit
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir)
                console.print(f"Created directory: {extract_dir}")
            else:
                console.print(
                    f"[warning]Directory already exists: [b]{extract_dir}[/]"
                    "\nRemove it manually to avoid conflicts"
                )

            with Progress(
                SpinnerColumn("dots12"),
                TextColumn(
                    "[progress.description]Outputs downloaded: {task.description}"
                ),
                console=error_console,
            ) as progress:
                task = progress.add_task(" - ")

                for i in itertools.count(start=1):
                    progress.update(task, description=f"{(i - 1) * 10}")
                    params["page"] = i
                    with disable_error_raise() as c:
                        res = c.get("/outputs/export", params=params)

                    if res.is_error:
                        progress.stop()
                        # List all extracted files
                        for root, _, files in os.walk(extract_dir):
                            for file in files:
                                console.print(os.path.join(root, file))
                        return 0

                    # Use io.BytesIO to treat the bytes as a file-like object
                    with (
                        io.BytesIO(res.content) as tar_buffer,
                        tarfile.open(fileobj=tar_buffer, mode="r:*") as tar,
                    ):
                        tar.extractall(path=extract_dir, filter="data")

                    # Extract files
                    for item in os.listdir(extract_dir):
                        item_path = os.path.join(extract_dir, item)
                    if os.path.isfile(item_path) and item.endswith(".tar.gz"):
                        base_name = item[:-7]  # Remove the ".tar.gz" extension
                        output_folder = os.path.join(extract_dir, base_name)
                        # Create the output folder if it doesn't exist
                        os.makedirs(output_folder, exist_ok=True)
                        with tarfile.open(item_path, "r:gz") as tar:
                            tar.extractall(path=output_folder, filter="data")
                        os.remove(item_path)
                    time.sleep(1)
        elif action == "delete":
            del params["page"]
            del params["limit"]
            if not force:
                console.print(
                    "[warning]This action will delete all reports that match the criteria[/]"
                )
                params["limit"] = 1
                res = client.get("/reports/search", params=params).json()
                if not res["total"]:
                    console.print("No reports found, nothing to delete")
                    return 0
                console.print(f"Total reports found: {res['total']}")
                answer = console.input("Do you want to delete these reports? (y/N): ")
                if answer.lower() != "y":
                    console.print("Action cancelled")
                    return 0

            console.print("Deleting reports...")
            res = client.delete("/reports", params=params)
            if res.is_success:
                console.print("Reports deleted successfully")
                return 0
            else:
                console.print("Failed to delete reports")
                return 1
        return 0

    @staticmethod
    def print_table(reports: list) -> None:
        autotable(
            [
                {
                    "id": report["id"],
                    # "team": report.get("team"),
                    "params": get_command_params(report.get("run_params")),
                    "playbook_path": report.get(
                        "playbook_path", report.get("playbook_uri")
                    ),
                    "playbook_name": report.get("playbook_name"),
                    "execution": report.get("execution"),
                    "status": report.get("status"),
                    "result": report.get("result"),
                    # "visibility": report.get("visibility"),
                    "runtime": execution_time(
                        report.get("execution_time", report.get("run_time"))
                    ),
                    # "user": report.get("user"),
                    "date": date_formatter(report.get("date")),
                }
                for report in reports
            ],
            widths=(16,),
        )
