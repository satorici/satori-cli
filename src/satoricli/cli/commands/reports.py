"""Download, search and delete reports from the server."""

import datetime
import json
import tarfile
from argparse import ArgumentParser
from math import ceil
from pathlib import Path
from typing import Any, Literal, Optional, get_args
from urllib.parse import urlencode

from msgspec import Struct, msgpack
from rich.live import Live
from rich.table import Table
from websockets.sync.client import connect

from satoricli.api import WS_HOST, client, ssl_ctx
from satoricli.cli.utils import (
    autoformat,
    autotable,
    console,
    date_formatter,
    execution_time,
    get_command_params,
)

from .base import BaseCommand

REPORT_VISIBILITY = Literal["public-global", "public", "unlisted", "private"]
RESULTS = Literal["pass", "fail", "unknown"]
PLAYBOOK_TYPE = Literal["public", "private"]
STATUS_FILTERS = Literal[
    "provisioning",
    "pending",
    "running",
    "completed",
    "stopped",
    "timeout",
]
EXECUTION_FILTERS = Literal["local", "run", "ci", "scan", "monitor"]


class ReportOutputDownloadData(Struct):
    report_id: str
    output: str
    report: bytes
    files: bytes | None


class ReportDownloadListData(Struct):
    total: int
    reports: list[ReportOutputDownloadData]


def _uppercase(s: Optional[str]) -> Optional[str]:
    return s.upper() if s else s


def add_pagination_args(parser: ArgumentParser) -> None:
    """Add common pagination arguments to a parser."""
    parser.add_argument("-p", "--page", type=int, default=1)
    parser.add_argument("-l", "--limit", type=int, default=10)


def advance_search_cursor(
    params: dict[str, Any],
    filters: dict[str, Any],
    *,
    pages_to_skip: int,
    page_size: int,
) -> bool:
    """Advance cursor-based search by skipping full pages. Returns False if results end early."""
    for _ in range(pages_to_skip):
        params["filters"] = json.dumps(filters)
        res = client.get("/reports/search", params=params).json()
        if not res["last_id"]:
            return False
        params["cursor"] = res.get("last_id")
    return True


def add_search_args(parser: ArgumentParser) -> None:
    parser.add_argument("-n", "--name", help="Export folder name")
    parser.add_argument(
        "--playbook-type",
        choices=get_args(PLAYBOOK_TYPE),
        default=None,
        help="Filter by playbook type",
    )
    parser.add_argument(
        "--visibility",
        choices=get_args(REPORT_VISIBILITY),
        help="Filter by report visibility",
    )
    parser.add_argument(
        "--result",
        choices=get_args(RESULTS),
        help="Filter by report result",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Filter by output string (support regex)",
    )
    parser.add_argument("--monitor", type=str, help="Filter by monitor ID")
    parser.add_argument("--playbook", type=str, help="Filter by playbook")
    parser.add_argument("--force", action="store_true", help="Force delete")
    parser.add_argument(
        "--status", choices=get_args(STATUS_FILTERS), help="Filter by status"
    )
    parser.add_argument(
        "--from",
        type=datetime.datetime.fromisoformat,
        help="Filter by from date",
        dest="from_date",
    )
    parser.add_argument(
        "--to",
        type=datetime.datetime.fromisoformat,
        help="Filter by to date",
        dest="to_date",
    )
    parser.add_argument(
        "--severity",
        action="append",
        default=None,
        type=str,
        help="Filter by output severity",
    )
    parser.add_argument(
        "--execution",
        choices=get_args(EXECUTION_FILTERS),
        default=None,
        type=str,
        help="Filter by execution ID",
    )
    parser.add_argument(
        "--from-report",
        type=str,
        help="Report ID to start search from",
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="Repository name",
    )
    parser.add_argument("--regex", action="store_true", help="Enable regex search")
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Enable case-sensitive search",
    )


class ReportsCommand(BaseCommand):
    name = "reports"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "--public",
            action="store_true",
            help="Fetch public reports",
        )
        add_pagination_args(parser)

        subparser = parser.add_subparsers(dest="action")

        search_parser = subparser.add_parser("search", aliases=["delete"])
        add_pagination_args(search_parser)
        add_search_args(search_parser)

        download_parser = subparser.add_parser("download")
        add_search_args(download_parser)

        stop_parser = subparser.add_parser("stop")
        add_search_args(stop_parser)

    def __call__(
        self,
        action: Optional[str],
        page: int = 1,
        limit: int = 10,
        filter: Optional[str] = None,
        public: bool = False,
        name: Optional[str] = None,
        playbook_type: Optional[PLAYBOOK_TYPE] = None,
        visibility: Optional[REPORT_VISIBILITY] = None,
        result: Optional[RESULTS] = None,
        query: Optional[str] = None,
        monitor: Optional[str] = None,
        playbook: Optional[str] = None,
        force: bool = False,
        status: Optional[STATUS_FILTERS] = None,
        from_date: Optional[datetime.datetime] = None,
        to_date: Optional[datetime.datetime] = None,
        severity: Optional[list[int]] = None,
        execution: Optional[EXECUTION_FILTERS] = None,
        from_report: Optional[str] = None,
        repo: Optional[str] = None,
        regex: bool = False,
        case_sensitive: bool = False,
        **kwargs,
    ):
        filters: dict[str, Any] = {}
        params: dict[str, Any] = {}
        if public:
            action = "search"
            visibility = "public-global"
        if action in ("delete", "search", "download", "stop"):
            filters = {
                "playbook_type": _uppercase(playbook_type),
                "report_visibility": "Public-Global"
                if visibility == "public-global"
                else _uppercase(visibility),
                "result": _uppercase(result),
                "query": query,
                "monitor": monitor,
                "playbook": playbook,
                "status": _uppercase(status),
                "severity": severity,
                "execution": execution,
                "repo": repo,
                "regexp": "1" if regex or case_sensitive else "0",
                "case_sensitive": "1" if case_sensitive else "0",
                "from_date": from_date,
                "to_date": to_date,
            }
            params = {
                "limit": limit,
            }

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

        if action in ("show", None):
            res = client.get(
                "/reports", params={"page": page, "limit": limit, "filters": filter}
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
            params["cursor"] = from_report
            if page > 1 and not advance_search_cursor(
                params, filters, pages_to_skip=page - 1, page_size=limit
            ):
                console.print("No reports found")
                return 1
            table = Table(expand=True)
            columns = [
                "ID",
                "Params",
                "Playbook Path",
                "Playbook Name",
                "Execution",
                "Status",
                "Result",
                "Runtime",
                "Date",
            ]
            for column in columns:
                table.add_column(column)

            with Live(table, refresh_per_second=1):
                params["filters"] = json.dumps(filters)
                res = client.get("/reports/search", params=params).json()
                for report in res["rows"]:
                    table.add_row(
                        report["id"],
                        get_command_params(report.get("run_params")),
                        report.get("playbook_path", report.get("playbook_uri")),
                        report.get("playbook_name"),
                        report.get("execution"),
                        report.get("status"),
                        report.get("result"),
                        execution_time(
                            report.get("execution_time", report.get("run_time"))
                        ),
                        date_formatter(report.get("date")),
                    )
            if not res["rows"]:
                console.print("No reports found")
                return 1
            console.print(f"Page {page}")
            return 0
        elif action == "download":
            # Save response
            extract_dir = name if name else "export"
            extract_root = Path(extract_dir)

            # Create directory if dont exit
            if not extract_root.exists():
                extract_root.mkdir(parents=True)
                console.print(f"Created directory: {extract_dir}")
            else:
                console.print(
                    f"[warning]Directory already exists: [b]{extract_dir}[/]"
                    "\nRemove it manually to avoid conflicts",
                )
            for subdir in ("outputs", "reports", "files"):
                (extract_root / subdir).mkdir(parents=True, exist_ok=True)

            filters_encoded = urlencode({"filters": json.dumps(filters)})
            with (
                console.status(
                    "Searching and downloading reports...",
                    spinner="dots12",
                ) as progress,
                connect(
                    f"{WS_HOST}/reports/download/ws?{filters_encoded}",
                    ssl=ssl_ctx if WS_HOST.startswith("wss://") else None,
                    additional_headers={
                        "Authorization": client.headers["Authorization"],
                    },
                    max_size=1024 * 1024 * 16,  # 16MB
                ) as websocket,
            ):
                # Get message from websocket, every message is a report encode with msgpack
                total_reports = 0
                for msg in websocket:
                    report: ReportDownloadListData = msgpack.decode(  # type: ignore
                        msg,  # type: ignore
                        type=ReportDownloadListData,
                    )
                    total_reports += len(report.reports)
                    for report_data in report.reports:
                        output_path = (
                            extract_root / "outputs" / f"{report_data.report_id}.txt"
                        )
                        with Path(output_path).open("w") as f:
                            f.write(report_data.output)
                        report_path = (
                            extract_root / "reports" / f"{report_data.report_id}.txt"
                        )
                        with Path(report_path).open("wb") as f:
                            f.write(report_data.report)
                        if report_data.files:
                            files_path = (
                                extract_root
                                / "files"
                                / f"{report_data.report_id}.tar.gz"
                            )
                            with Path(files_path).open("wb") as f:
                                f.write(report_data.files)
                    progress.update(f"Downloaded {total_reports} reports")

                progress.update("Extracting files...")
                # Extract files
                for item_path in extract_root.iterdir():
                    if item_path.is_file() and item_path.name.endswith(".tar.gz"):
                        base_name = item_path.name[
                            :-7
                        ]  # Remove the ".tar.gz" extension
                        output_folder = extract_root / base_name
                        output_folder.mkdir(parents=True, exist_ok=True)
                        with tarfile.open(item_path, "r:gz") as tar:
                            tar.extractall(path=output_folder, filter="data")
                        item_path.unlink()
                console.print("Reports downloaded successfully")
        elif action == "delete":
            console.print(
                "[warning]This action will delete all reports that match the criteria[/]"
            )
            params["limit"] = 1
            console.print("Searching for reports...")
            filters_encoded = urlencode({"filters": json.dumps(filters)})
            with connect(
                f"{WS_HOST}/reports/delete/ws?{filters_encoded}",
                ssl=ssl_ctx if WS_HOST.startswith("wss://") else None,
                additional_headers={
                    "Authorization": client.headers["Authorization"],
                },
            ) as websocket:
                res: str | bytes = websocket.recv()

                message = json.loads(res)
                if "error" in message:
                    console.print(message["error"])
                    return 1
                if not message.get("total"):
                    console.print("No reports found, nothing to delete")
                    return 0
                console.print(message["message"])
                if not force:
                    answer = console.input(
                        "Do you want to delete these reports? (y/N): "
                    )
                    if answer.lower() != "y":
                        console.print("Action cancelled")
                        return 0
                console.print("Deleting reports...")
                websocket.send("delete")
                for msg in websocket:
                    res_decode = json.loads(msg)
                    if "error" in res_decode:
                        console.print(res_decode["error"])
                        return 1
                    console.print(res_decode["message"])
            return 0
        elif action == "stop":
            del params["page"]
            if not filters.get("status"):
                filters["status"] = "Running"
            if not force:
                console.print(
                    "[warning]This action will stop all reports that match the criteria[/]"
                )
                params["limit"] = 1
                params["user_reports"] = True
                res = client.get(
                    "/reports/search",
                    params=params | {"filters": json.dumps(filters)},
                ).json()
                if not res["total"]:
                    console.print("No reports found, nothing to stop")
                    return 0
                console.print(f"Total reports found: {res['total']}")
                answer = console.input("Do you want to stop these reports? (y/N): ")
                if answer.lower() != "y":
                    console.print("Action cancelled")
                    return 0

            del params["limit"]
            console.print("Stopping reports...")
            res = client.patch("/reports/stop", json=filters)
            if res.is_success:
                console.print("Reports stopped successfully")
                return 0
            console.print("Failed to stop reports")
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
