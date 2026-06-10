"""Download, search and delete reports from the server."""

import datetime
import json
import tarfile
import time
from argparse import ArgumentParser
from collections.abc import Callable
from math import ceil
from pathlib import Path
from typing import Any, Literal, Optional, Union, get_args
from urllib.parse import urlencode

import httpx
import msgspec
from msgspec import Struct, msgpack
from rich.live import Live
from rich.table import Table
from websockets.exceptions import ConnectionClosed, InvalidStatus
from websockets.sync.client import ClientConnection, connect

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
    files_url: str | None


class ReportDownloadListData(Struct):
    total: int
    reports: list[ReportOutputDownloadData]


class ReportDownloadDoneData(Struct):
    done: bool
    failed_count: int
    error: str | None


class UserExportInfo(Struct):
    key: str
    created: int
    size: int


class ReportExportStatusData(Struct):
    status: Literal["in_progress", "ready", "none", "error"]
    export: UserExportInfo | None = None
    error: str | None = None
    progress: int | None = None
    total: int | None = None
    processed: int | None = None
    failed_count: int | None = None


class ReportExportDownloadData(Struct):
    url: str
    created: int
    size: int


class ReportExportCreateData(Struct):
    status: Literal["started", "in_progress"]


class ReportExportAction(Struct):
    action: Literal["download", "create", "status"]


class ReportExportErrorData(Struct):
    error: str


ExportFrame = Union[
    ReportExportStatusData,
    ReportExportDownloadData,
    ReportExportCreateData,
    ReportExportErrorData,
]

ExportMessageKind = Literal["initial", "status", "create", "download"]


class ReportExportError(Exception):
    """Raised when the export websocket returns an error frame."""


DOWNLOAD_RECONNECT_ATTEMPTS = 5
DEFAULT_EXPORT_ARCHIVE = "reports-export.tar.gz"
DEFAULT_EXPORT_DIR = "export"
EXPORT_POLL_INTERVAL_SECONDS = 3.0


def _uppercase(s: Optional[str]) -> Optional[str]:
    return s.upper() if s else s


def add_pagination_args(parser: ArgumentParser) -> None:
    """Add common pagination arguments to a parser."""
    parser.add_argument("-p", "--page", type=int, default=1)
    parser.add_argument("-l", "--limit", type=int, default=10)


def _download_ws_headers() -> dict[str, str]:
    headers = {"Authorization": client.headers["Authorization"]}
    if team := client.headers.get("Satori-Team"):
        headers["Satori-Team"] = team
    return headers


def _download_ws_query(filters_json: str, after_id: str | None = None) -> str:
    params: dict[str, str] = {"filters": filters_json}
    if after_id:
        params["after_id"] = after_id
    return urlencode(params)


def _decode_download_frame(
    msg: bytes | str,
) -> ReportDownloadListData | ReportDownloadDoneData:
    if isinstance(msg, str):
        msg = msg.encode()
    payload = msgpack.decode(msg)
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected download frame type: {type(payload)!r}")
    if "reports" in payload:
        return msgspec.convert(payload, ReportDownloadListData)
    if "done" in payload:
        return msgspec.convert(payload, ReportDownloadDoneData)
    raise ValueError(f"Unknown download frame keys: {sorted(payload)}")


def _existing_report_ids(extract_root: Path) -> set[str]:
    outputs_dir = extract_root / "outputs"
    if not outputs_dir.is_dir():
        return set()
    return {path.stem for path in outputs_dir.glob("*.txt")}


def _save_report(
    report_data: ReportOutputDownloadData,
    extract_root: Path,
) -> None:
    output_path = extract_root / "outputs" / f"{report_data.report_id}.txt"
    with output_path.open("w") as f:
        f.write(report_data.output)
    report_path = extract_root / "reports" / f"{report_data.report_id}.txt"
    with report_path.open("wb") as f:
        f.write(report_data.report)
    if report_data.files_url:
        files_path = extract_root / "files" / f"{report_data.report_id}.tar.gz"
        with httpx.stream("GET", report_data.files_url) as response:
            response.raise_for_status()
            with files_path.open("wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)


def _extract_downloaded_files(extract_root: Path) -> None:
    files_dir = extract_root / "files"
    for item_path in files_dir.iterdir():
        if item_path.is_file() and item_path.name.endswith(".tar.gz"):
            base_name = item_path.name.removesuffix(".tar.gz")
            output_folder = extract_root / base_name
            output_folder.mkdir(parents=True, exist_ok=True)
            with tarfile.open(item_path, "r:gz") as tar:
                tar.extractall(path=output_folder, filter="data")
            item_path.unlink()


def _run_report_download(
    extract_root: Path,
    filters: dict[str, Any],
    *,
    on_progress: Callable[[str], None] | None = None,
) -> int:
    def update_status(message: str) -> None:
        if on_progress is not None:
            on_progress(message)

    filters_json = json.dumps(filters)
    saved_ids = _existing_report_ids(extract_root)
    last_received_report_id: str | None = None
    session_downloaded = 0
    done_frame: ReportDownloadDoneData | None = None
    ws_ssl = ssl_ctx if WS_HOST.startswith("wss://") else None
    headers = _download_ws_headers()

    for attempt in range(DOWNLOAD_RECONNECT_ATTEMPTS):
        query = _download_ws_query(
            filters_json,
            after_id=last_received_report_id,
        )
        disconnect_reason: str | None = None
        try:
            with connect(
                f"{WS_HOST}/reports/download/ws?{query}",
                ssl=ws_ssl,
                additional_headers=headers,
                max_size=1024 * 1024 * 16,  # 16MB
            ) as websocket:
                for msg in websocket:
                    frame = _decode_download_frame(msg)
                    if isinstance(frame, ReportDownloadDoneData):
                        done_frame = frame
                        break
                    for report_data in frame.reports:
                        last_received_report_id = report_data.report_id
                        if report_data.report_id in saved_ids:
                            continue
                        _save_report(report_data, extract_root)
                        saved_ids.add(report_data.report_id)
                        session_downloaded += 1
                    update_status(f"Downloaded {len(saved_ids)} reports")
        except InvalidStatus as exc:
            if exc.response.status_code == 404:
                console.print(
                    "[error]Report not found (invalid after_id for resume)[/]"
                )
                return 1
            raise
        except ConnectionClosed as exc:
            disconnect_reason = f"{exc.code} {exc.reason or 'no reason'}"
            update_status(
                f"Connection closed ({disconnect_reason}), will resume from last report"
            )
        except OSError:
            disconnect_reason = "network error"
            update_status("Network error, will resume from last report")

        if done_frame is not None:
            break

        if attempt < DOWNLOAD_RECONNECT_ATTEMPTS - 1:
            delay = 2**attempt
            if disconnect_reason:
                update_status(
                    f"Connection lost ({disconnect_reason}), resuming in {delay}s "
                    f"(attempt {attempt + 2}/{DOWNLOAD_RECONNECT_ATTEMPTS})"
                )
            else:
                update_status(
                    f"Connection lost, resuming in {delay}s "
                    f"(attempt {attempt + 2}/{DOWNLOAD_RECONNECT_ATTEMPTS})"
                )
            time.sleep(delay)
    else:
        console.print(
            "[error]Download interrupted: connection closed before export completed[/]"
        )
        return 1

    if not done_frame.done:
        message = done_frame.error or "Export failed"
        console.print(f"[error]{message}[/]")
        if done_frame.failed_count:
            console.print(
                f"[error]{done_frame.failed_count} report(s) could not be downloaded[/]"
            )
        return 1

    if done_frame.failed_count:
        console.print(
            f"[warning]Export finished but {done_frame.failed_count} report(s) "
            "could not be downloaded[/]"
        )

    if not saved_ids:
        console.print("No reports found")
        return 0

    update_status("Extracting files...")
    _extract_downloaded_files(extract_root)
    if session_downloaded:
        console.print(
            f"Downloaded {session_downloaded} new report(s) ({len(saved_ids)} total)"
        )
    console.print("Reports downloaded successfully")
    return 0


def _format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    units = ("KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        value /= 1024
        if value < 1024 or unit == units[-1]:
            if unit == "KB":
                return f"{value:.0f} {unit}"
            return f"{value:.1f} {unit}"
    return f"{size} B"


def _format_export_timestamp(created: int) -> str:
    return datetime.datetime.fromtimestamp(
        created,
        tz=datetime.timezone.utc,
    ).strftime("%Y-%m-%d %H:%M:%S UTC")


def _export_report_counts(
    status: ReportExportStatusData,
) -> tuple[int | None, int | None, int | None]:
    processed = status.processed
    total = status.total
    remaining = None
    if total is not None and processed is not None:
        remaining = max(total - processed, 0)
    return processed, total, remaining


def _format_export_progress(status: ReportExportStatusData) -> str | None:
    processed, total, remaining = _export_report_counts(status)
    parts: list[str] = []
    if processed is not None and total is not None:
        parts.append(f"{processed}/{total} reports exported")
        if remaining is not None:
            parts.append(f"{remaining} remaining")
    if status.progress is not None:
        parts.append(f"{status.progress}%")
    if not parts:
        return None
    return ", ".join(parts)


def _decode_export_frame(
    msg: bytes | str,
    *,
    expected: ExportMessageKind | None = None,
) -> ExportFrame:
    if isinstance(msg, str):
        msg = msg.encode()
    payload = msgpack.decode(msg)
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected export frame type: {type(payload)!r}")

    if set(payload) == {"error"}:
        return msgspec.convert(payload, ReportExportErrorData)

    if "url" in payload:
        return msgspec.convert(payload, ReportExportDownloadData)

    status = payload.get("status")
    if status in {"started", "in_progress"} and expected == "create":
        return msgspec.convert(payload, ReportExportCreateData)

    if status in {"in_progress", "ready", "none", "error"}:
        return msgspec.convert(payload, ReportExportStatusData)

    if status in {"started", "in_progress"}:
        return msgspec.convert(payload, ReportExportCreateData)

    raise ValueError(f"Unknown export frame keys: {sorted(payload)}")


class ReportExportClient:
    def __init__(
        self,
        poll_interval: float = EXPORT_POLL_INTERVAL_SECONDS,
    ) -> None:
        self.poll_interval = poll_interval
        self._ws: ClientConnection | None = None

    def connect(self) -> ReportExportStatusData:
        if self._ws is not None:
            raise RuntimeError("Report export websocket is already connected")

        ws_ssl = ssl_ctx if WS_HOST.startswith("wss://") else None
        try:
            self._ws = connect(
                f"{WS_HOST}/reports/export/ws",
                ssl=ws_ssl,
                additional_headers=_download_ws_headers(),
            )
        except InvalidStatus as exc:
            if exc.response.status_code in (401, 403):
                raise ReportExportError(
                    "Authentication failed for report export websocket"
                ) from exc
            raise ReportExportError(
                f"Failed to connect to report export websocket "
                f"(HTTP {exc.response.status_code})"
            ) from exc

        status = self._recv(expected="initial")
        if not isinstance(status, ReportExportStatusData):
            raise ReportExportError("Unexpected initial export websocket frame")
        if status.status == "error":
            raise ReportExportError(status.error or "Export status error")
        return status

    def disconnect(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    def get_status(self) -> ReportExportStatusData:
        self._send_action("status")
        return self._expect_status(self._recv(expected="status"))

    def create_export(self) -> ReportExportCreateData:
        self._send_action("create")
        frame = self._recv(expected="create")
        if isinstance(frame, ReportExportErrorData):
            raise ReportExportError(frame.error)
        if isinstance(frame, ReportExportCreateData):
            return frame
        if isinstance(frame, ReportExportStatusData):
            if frame.status in {"started", "in_progress"}:
                return ReportExportCreateData(status=frame.status)  # type: ignore[arg-type]
            if frame.status == "error":
                raise ReportExportError(frame.error or "Failed to start export")
        raise ReportExportError("Unexpected response while starting export")

    def download_export(self) -> ReportExportDownloadData:
        self._send_action("download")
        frame = self._recv(expected="download")
        if isinstance(frame, ReportExportErrorData):
            raise ReportExportError(frame.error)
        if isinstance(frame, ReportExportDownloadData):
            return frame
        raise ReportExportError("Unexpected response while downloading export")

    def wait_until_ready(
        self,
        *,
        on_poll: Callable[[ReportExportStatusData], None] | None = None,
    ) -> ReportExportStatusData:
        while True:
            status = self.get_status()
            if on_poll is not None:
                on_poll(status)
            if status.status == "ready":
                return status
            if status.status == "error":
                raise ReportExportError(status.error or "Export failed")
            if status.status == "none":
                raise ReportExportError("Export is not available")
            time.sleep(self.poll_interval)

    def _send_action(self, action: Literal["download", "create", "status"]) -> None:
        if self._ws is None:
            raise RuntimeError("Report export websocket is not connected")
        self._ws.send(msgpack.encode(ReportExportAction(action=action)))

    def _recv(self, *, expected: ExportMessageKind) -> ExportFrame:
        if self._ws is None:
            raise RuntimeError("Report export websocket is not connected")
        try:
            msg = self._ws.recv()
        except ConnectionClosed as exc:
            raise ReportExportError(
                f"Report export websocket closed ({exc.code} {exc.reason or ''})"
            ) from exc
        return _decode_export_frame(msg, expected=expected)

    @staticmethod
    def _expect_status(frame: ExportFrame) -> ReportExportStatusData:
        if isinstance(frame, ReportExportErrorData):
            raise ReportExportError(frame.error)
        if isinstance(frame, ReportExportStatusData):
            return frame
        raise ReportExportError("Unexpected status response from export websocket")


def _describe_export_status(status: ReportExportStatusData) -> str:
    if status.status == "ready" and status.export is not None:
        export = status.export
        return (
            f"Export ready ({_format_export_timestamp(export.created)}, "
            f"{_format_file_size(export.size)})"
        )
    if status.status == "in_progress":
        processed, total, remaining = _export_report_counts(status)
        if processed is not None and total is not None:
            message = f"Exporting reports {processed}/{total}"
            if remaining is not None:
                message = f"{message}, {remaining} left"
        else:
            message = "Export in progress"
        if status.progress is not None:
            message = f"{message} ({status.progress}%)"
        if status.failed_count:
            message = f"{message}, {status.failed_count} failed"
        return message
    if status.status == "none":
        return "No export available"
    if status.status == "error":
        return status.error or "Export failed"
    return f"Export status: {status.status}"


def _download_export_archive(url: str, output_path: Path) -> None:
    with httpx.stream("GET", url) as response:
        response.raise_for_status()
        with output_path.open("wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)


def _extract_export_archive(archive_path: Path, extract_root: Path) -> None:
    extract_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=extract_root, filter="data")
    if (extract_root / "files").is_dir():
        _extract_downloaded_files(extract_root)


def _display_export_info(status: ReportExportStatusData) -> None:
    if status.status == "ready" and status.export is not None:
        export = status.export
        console.print("[bold]reports-export.tar.gz[/]")
        console.print(f"  Created: {_format_export_timestamp(export.created)}")
        console.print(f"  Size:    {_format_file_size(export.size)}")
        return

    if status.status == "in_progress":
        console.print("Export is currently in progress.")
        processed, total, remaining = _export_report_counts(status)
        if processed is not None and total is not None:
            console.print(f"  Exported:  {processed}/{total} reports")
            console.print(f"  Remaining: {remaining} reports")
        elif progress := _format_export_progress(status):
            console.print(f"  Progress:  {progress}")
        elif status.progress is not None:
            console.print(f"  Progress:  {status.progress}%")
        if status.failed_count:
            console.print(f"  Failed:    {status.failed_count}")
        return

    if status.status == "none":
        console.print("No export available.")
        return

    if status.status == "error":
        console.print(f"[error]{status.error or 'Export failed'}[/]")


def _prompt_export_choice(
    status: ReportExportStatusData,
) -> Literal["download", "create", "wait", "cancel"]:
    if status.status == "ready":
        answer = (
            console.input(
                "Download this export or generate a new one? "
                "(d)ownload/(g)enerate/(c)ancel: ",
            )
            .strip()
            .lower()
        )
        if answer in {"d", "download", ""}:
            return "download"
        if answer in {"g", "generate", "new"}:
            return "create"
        return "cancel"

    if status.status == "none":
        answer = console.input("Generate a new export? (y/N): ").strip().lower()
        return "create" if answer == "y" else "cancel"

    if status.status == "in_progress":
        answer = console.input("Wait for the export to finish? (Y/n): ").strip().lower()
        return "wait" if answer in {"", "y", "yes"} else "cancel"

    if status.status == "error":
        answer = console.input("Generate a new export? (y/N): ").strip().lower()
        return "create" if answer == "y" else "cancel"

    return "cancel"


def _run_report_export(output_path: Path) -> int:
    extract_root = Path(DEFAULT_EXPORT_DIR)
    export_client = ReportExportClient()
    try:
        with console.status(
            "Connecting to report export service...",
            spinner="dots12",
        ):
            status = export_client.connect()

        while True:
            console.print()
            _display_export_info(status)
            choice = _prompt_export_choice(status)
            if choice == "cancel":
                console.print("Action cancelled")
                return 0

            if choice == "wait":
                with console.status(
                    "Waiting for export...", spinner="dots12"
                ) as progress:
                    status = export_client.wait_until_ready(
                        on_poll=lambda polled: progress.update(
                            _describe_export_status(polled)
                        ),
                    )
                continue

            if choice == "create":
                with console.status(
                    "Generating export...", spinner="dots12"
                ) as progress:
                    progress.update("Starting export...")
                    export_client.create_export()
                    status = export_client.wait_until_ready(
                        on_poll=lambda polled: progress.update(
                            _describe_export_status(polled)
                        ),
                    )
                continue

            if status.status != "ready":
                raise ReportExportError("No export available to download")

            if extract_root.exists() and any(extract_root.iterdir()):
                console.print(
                    f"[warning]Directory already exists: [b]{DEFAULT_EXPORT_DIR}[/]"
                    "\nExtracting may overwrite existing files",
                )

            with console.status("Downloading export...", spinner="dots12") as progress:
                progress.update("Requesting download URL...")
                download_data = export_client.download_export()
                progress.update(
                    f"Downloading {_format_file_size(download_data.size)} archive..."
                )
                _download_export_archive(download_data.url, output_path)
                progress.update("Extracting archive...")
                _extract_export_archive(output_path, extract_root)
            break
    except ReportExportError as exc:
        console.print(f"[error]{exc}[/]")
        return 1
    except httpx.HTTPError as exc:
        console.print(f"[error]Failed to download export archive: {exc}[/]")
        return 1
    finally:
        export_client.disconnect()

    console.print(f"Export saved to {output_path}")
    console.print(f"Reports extracted to {extract_root}")
    return 0


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
        type=str.lower,
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

        subparser.add_parser("export")

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

            with console.status(
                "Searching and downloading reports...",
                spinner="dots12",
            ) as progress:
                return _run_report_download(
                    extract_root,
                    filters,
                    on_progress=progress.update,
                )
        elif action == "export":
            return _run_report_export(Path(DEFAULT_EXPORT_ARCHIVE))
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
