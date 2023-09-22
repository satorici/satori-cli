import json
import os
import shutil
import tempfile
import time
import uuid
import warnings
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

import httpx
import yaml
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.progress import open as progress_open
from satorici.validator import validate_playbook
from satorici.validator.exceptions import (
    NoExecutionsError,
    PlaybookValidationError,
    PlaybookVariableError,
)
from satorici.validator.warnings import NoLogMonitorWarning

from satoricli.api import client, configure_client
from satoricli.bundler import get_local_files, make_bundle
from satoricli.utils import load_config
from satoricli.validations import get_parameters, has_executions, validate_parameters

from ..utils import autoformat, check_monitor, console, error_console, format_outputs
from .base import BaseCommand


def validate_config(playbook: Path, params: set):
    try:
        config = yaml.safe_load(playbook.read_text())
    except yaml.YAMLError as e:
        error_console.print(
            f"Error parsing the playbook [bold]{playbook.name}[/]:\n", e
        )
        return False

    try:
        with warnings.catch_warnings(record=True) as w:
            validate_playbook(config)

        for warning in w:
            if warning.category == NoLogMonitorWarning:
                error_console.print(
                    "[warning]WARNING:[/] No notifications (log, onLogFail or "
                    "onLogPass) were defined for the Monitor"
                )
    except TypeError:
        error_console.print("Error: playbook must be a mapping type")
        return False
    except (PlaybookVariableError, NoExecutionsError):
        pass
    except PlaybookValidationError as e:
        error_console.print(
            f"Validation error on playbook [bold]{playbook.name}[/]:\n", e
        )
        return False

    if not has_executions(config, playbook.parent):
        error_console.print("[error]No executions found")
        return False

    variables = get_parameters(config)

    if variables - params:
        error_console.print(f"[error]Required parameters: {variables - params}")
        return False

    return True


def missing_ymls(root: str):
    satori_yml = Path(root, ".satori.yml")
    local_ymls = list(filter(lambda p: p.is_file(), Path(root).rglob(".satori.yml")))
    imported = get_local_files(yaml.safe_load(satori_yml.read_text()))["imports"]

    if len(local_ymls) > 1 and len(local_ymls) - 1 > len(imported):
        return True

    return False


def make_packet(path: str):
    temp_file = Path(tempfile.gettempdir(), str(uuid.uuid4()))
    shutil.make_archive(str(temp_file), "gztar", path)
    return f"{temp_file}.tar.gz"


def run_folder(bundle, packet: str, secrets: Optional[str], is_monitor: bool) -> str:
    run_info = client.post(
        "/runs/archive", json={"secrets": secrets or "", "is_monitor": is_monitor}
    ).json()
    arc = run_info["archive"]
    bun = run_info["bundle"]

    try:
        with progress_open(
            packet, "rb", description="Uploading...", console=error_console
        ) as f:
            res = httpx.post(arc["url"], data=arc["fields"], files={"file": f})
        res.raise_for_status()
    finally:
        os.remove(packet)

    res = httpx.post(bun["url"], data=bun["fields"], files={"file": bundle})
    res.raise_for_status()

    return run_info["monitor"] if is_monitor else run_info["report_id"]


def run_file(bundle, secrets: Optional[str], is_monitor: bool) -> str:
    run_info = client.post(
        "/runs/bundle", json={"secrets": secrets or "", "is_monitor": is_monitor}
    ).json()
    res = httpx.post(
        run_info["url"], data=run_info["fields"], files={"file": bundle}, timeout=None
    )
    res.raise_for_status()

    return run_info["monitor"] if is_monitor else run_info["report_id"]


def run_url(url: str, secrets: Optional[str]) -> str:
    info = client.post(
        "/runs/url", json={"secrets": secrets or "", "is_monitor": False, "url": url}
    ).json()
    return info["report_id"]


class RunCommand(BaseCommand):
    name = "run"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("path", metavar="PATH")
        parser.add_argument("-s", "--sync", action="store_true")
        parser.add_argument("-d", "--data", type=json.loads)
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-o", "--output", action="store_true")
        group.add_argument("-r", "--report", action="store_true")
        group.add_argument("-f", "--files", action="store_true")

    def __call__(
        self,
        path: str,
        sync: bool,
        data: Optional[dict],
        output: bool,
        report: bool,
        files: bool,
        **kwargs,
    ):
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])

        is_sync = sync or output or report or files
        target = Path(path)

        if data:
            if not validate_parameters(data):
                raise ValueError("Malformed parameters")

            params = set(data.keys())
            data = str(data)  # TODO: Modify API to receive JSON
        else:
            params = set()

        if target.is_dir() and (target / ".satori.yml").is_file():
            playbook = target / ".satori.yml"
        elif target.is_file():
            playbook = target
        elif path.startswith("satori://"):
            playbook = None
        else:
            error_console.print("[error]Playbook file or folder not found")
            return 1

        if playbook and not validate_config(playbook, params):
            return 1

        if target.is_dir():
            bundle = make_bundle(playbook, from_dir=True)
            packet = make_packet(path)
            is_monitor: bool = check_monitor(playbook)

            if missing_ymls(path):
                error_console.print(
                    "[warning]WARNING:[/] There are some .satori.yml outside the root "
                    "folder that have not been imported."
                )

            run_id = run_folder(bundle, packet, data, is_monitor)
        elif target.is_file():
            bundle = make_bundle(playbook)
            is_monitor: bool = check_monitor(playbook)
            run_id = run_file(bundle, data, is_monitor)
        elif path.startswith("satori://"):
            is_monitor = False
            run_id = run_url(path, data)
        else:
            return 1

        if is_sync and not is_monitor:
            return run_sync(run_id, output, report, files, kwargs["json"])

        if kwargs["json"]:
            console.print_json(data={"id": run_id, "monitor": is_monitor})
        else:
            console.print("Monitor" if is_monitor else "Report", "ID:", run_id)

            if is_monitor:
                console.print(f"Monitor: https://www.satori-ci.com/monitor?id={run_id}")
            else:
                console.print(
                    f"Report: https://www.satori-ci.com/report_details/?n={run_id}"
                )


def run_sync(report_id: str, output: bool, report: bool, files: bool, print_json: bool):
    info_console = error_console if print_json else console
    info_console.print("Report ID:", report_id)
    info_console.print(
        f"Report: https://www.satori-ci.com/report_details/?n={report_id}"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]Status: {task.description}"),
        TimeElapsedColumn(),
        console=error_console,
    ) as progress:
        task = progress.add_task("Fetching data")
        status = "Unknown"

        while status not in ("Completed", "Undefined"):
            try:
                report_data = client.get(f"/reports/{report_id}").json()
                status = report_data.get("status", "Unknown")
            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    status = "Unknown"
                else:
                    return 1

            progress.update(task, description=status)
            time.sleep(1)

    result = report_data.get("result", "Unknown")
    if not any((report, output, files)) or result == "Unknown":
        if comments := report_data.get("user_warnings"):
            error_console.print(f"[warning]WARNING:[/] {comments}")

        if result == "Unknown":
            console.print("Result: Unknown")
            return 1

        fails = report_data["fails"]

        if print_json:
            console.print_json(
                data={
                    "report_id": report_id,
                    "result": "Pass" if not fails else f"Fail({fails})",
                }
            )
        else:
            console.print("Result:", "Pass" if not fails else f"Fail({fails})")

        return 0 if fails == 0 else 1

    if report:
        report_out = []
        # Remove keys
        json_data = report_data.get("report") or []
        for report in json_data:
            report_out.append(report)
            asserts = []
            for asrt in report["asserts"]:
                asrt.pop("count", None)
                asrt.pop("description", None)
                if len(asrt.get("data", [])) == 0:
                    asrt.pop("data", None)
                asserts.append(asrt)
        if print_json:
            console.print_json(data=report_out)
        else:
            autoformat(report_out, list_separator="- " * 20)
    elif output:
        r = client.get(f"/outputs/{report_id}")
        with httpx.stream("GET", r.json()["url"], timeout=300) as s:
            if print_json:
                for line in s.iter_lines():
                    console.print(line)
            else:
                format_outputs(s.iter_lines())
    elif files:
        r = client.get(f"/outputs/{report_id}/files")
        with httpx.stream("GET", r.json()["url"]) as s:
            total = int(s.headers["Content-Length"])

            with Progress(console=error_console) as progress:
                task = progress.add_task("Downloading...", total=total)

                with open(f"satorici-files-{report_id}.tar.gz", "wb") as f:
                    for chunk in s.iter_raw():
                        progress.update(task, advance=len(chunk))
                        f.write(chunk)
