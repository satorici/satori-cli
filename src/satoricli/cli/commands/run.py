import json
import os
import shutil
import tempfile
import uuid
import warnings
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

import httpx
import yaml
from rich.progress import open as progress_open
from satorici.validator import validate_playbook
from satorici.validator.exceptions import (
    NoExecutionsError,
    PlaybookValidationError,
    PlaybookVariableError,
)
from satorici.validator.warnings import (
    MissingAssertionsWarning,
    MissingNameWarning,
    NoLogMonitorWarning,
)
from satoricli.api import client
from satoricli.bundler import get_local_files, make_bundle
from satoricli.validations import get_parameters, has_executions, validate_parameters

from ..utils import (
    check_monitor,
    console,
    download_files,
    error_console,
    print_output,
    print_summary,
    wait,
)
from .base import BaseCommand
from .report import ReportCommand


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
            elif warning.category == MissingAssertionsWarning:
                error_console.print("[warning]WARNING:[/] No asserts were defined")
            elif warning.category == MissingNameWarning:
                error_console.print("[warning]WARNING:[/] No name was defined")
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


def has_files(playbook_path: Path):
    try:
        return yaml.safe_load(playbook_path.read_text())["settings"]["files"]
    except Exception:
        return False


class RunCommand(BaseCommand):
    name = "run"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("path", metavar="PATH")
        parser.add_argument("-d", "--data", type=json.loads)
        group = parser.add_argument_group()
        group.add_argument("-s", "--sync", action="store_true")
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

        if files and playbook and not has_files(playbook):
            error_console.print(
                "[error]ERROR:[/] Can't use --files without files setting in playbook"
            )
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

        if kwargs["json"]:
            console.print_json(data={"id": run_id, "monitor": is_monitor})
        else:
            console.print("Monitor" if is_monitor else "Report", "ID:", run_id)

            if is_monitor:
                console.print(f"Monitor: https://satori.ci/monitor?id={run_id}")
            else:
                console.print(f"Report: https://satori.ci/report_details/?n={run_id}")

        if is_monitor:
            return

        if sync or report or output or files:
            wait(run_id)

        ret = print_summary(run_id, kwargs["json"]) if sync else 0

        if report:
            ReportCommand.print_report_asrt(run_id, kwargs["json"])

        if output:
            print_output(run_id, kwargs["json"])

        if files and playbook and has_files(playbook):
            download_files(run_id)

        return ret
