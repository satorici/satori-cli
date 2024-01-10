import json
import os
import shutil
import tempfile
import uuid
import warnings
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Optional

import httpx
import yaml
from rich.progress import open as progress_open
from satorici.validator import validate_settings
from satoricli.api import client
from satoricli.bundler import make_bundle
from satoricli.validations import validate_parameters

from ..utils import (
    console,
    download_files,
    error_console,
    missing_ymls,
    print_output,
    print_summary,
    validate_config,
    wait,
)
from .base import BaseCommand
from .report import ReportCommand


def make_packet(path: str):
    temp_file = Path(tempfile.gettempdir(), str(uuid.uuid4()))
    shutil.make_archive(str(temp_file), "gztar", path)
    return f"{temp_file}.tar.gz"


def new_run(
    *,
    path: str,
    bundle: Optional[Any] = None,
    packet: Optional[Path] = None,
    secrets: Optional[dict] = None,
    settings: Optional[dict] = None,
) -> list[str]:
    data = client.post(
        "/runs",
        data={
            "path": path,
            "secrets": json.dumps(secrets) if secrets else None,
            "settings": json.dumps(settings) if settings else None,
            "with_files": bool(packet),
        },
        files={"bundle": bundle} if bundle else {"": ""},
    ).json()

    if arc := data["upload_data"]:
        try:
            with progress_open(
                packet, "rb", description="Uploading...", console=error_console
            ) as f:
                res = httpx.post(arc["url"], data=arc["fields"], files={"file": f})
            res.raise_for_status()
        finally:
            os.remove(packet)

    return data["report_ids"]


def new_monitor(
    bundle,
    settings: dict,
    *,
    packet: Optional[Path] = None,
    secrets: Optional[dict] = None,
) -> str:
    data = client.post(
        "/monitors",
        data={
            "secrets": json.dumps(secrets) if secrets else None,
            "settings": json.dumps(settings),
            "with_files": bool(packet),
        },
        files={"bundle": bundle} if bundle else {"": ""},
    ).json()

    if arc := data["upload_data"]:
        try:
            with progress_open(
                packet, "rb", description="Uploading...", console=error_console
            ) as f:
                res = httpx.post(arc["url"], data=arc["fields"], files={"file": f})
            res.raise_for_status()
        finally:
            os.remove(packet)

    return data["monitor_id"]


def has_files(playbook_path: Path):
    try:
        return yaml.safe_load(playbook_path.read_text())["settings"]["files"]
    except Exception:
        return False


def get_cli_settings(args: dict):
    keys = ("cpu", "memory", "cron", "rate", "count", "name", "timeout")

    return {key: value for key, value in args.items() if key in keys and value}


def warn_settings(settings: dict):
    with warnings.catch_warnings(record=True) as ws:
        validate_settings(settings)

        for w in ws:
            error_console.print("WARNING:", w.message)


class RunCommand(BaseCommand):
    name = "run"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("path", metavar="PATH")
        parser.add_argument("-d", "--data", type=json.loads)
        parser.add_argument(
            "-p",
            "--playbook",
            type=Path,
            help="if PATH is a directory this playbook will be used",
        )

        settings = parser.add_argument_group("run settings")
        monitor = settings.add_mutually_exclusive_group()
        monitor.add_argument("--rate")
        monitor.add_argument("--cron")
        settings.add_argument("--name")
        settings.add_argument("--count", type=int)
        settings.add_argument("--cpu", type=int)
        settings.add_argument("--memory", type=int)
        settings.add_argument("--timeout", type=int)

        sync = parser.add_argument_group("sync run")
        sync.add_argument("-s", "--sync", action="store_true")
        sync.add_argument("-o", "--output", action="store_true")
        sync.add_argument("-r", "--report", action="store_true")
        sync.add_argument("-f", "--files", action="store_true")

    def __call__(
        self,
        path: str,
        sync: bool,
        data: Optional[dict],
        playbook: Optional[Path],
        output: bool,
        report: bool,
        files: bool,
        **kwargs,
    ):
        if data and not validate_parameters(data):
            raise ValueError("Malformed parameters")

        cli_settings = get_cli_settings(kwargs)
        is_monitor = bool(cli_settings.get("rate") or cli_settings.get("cron"))

        if path.startswith("satori://"):
            warn_settings(cli_settings)
            ids = new_run(path=path, secrets=data, settings=cli_settings)
            is_monitor = False
            monitor_id = None
        elif (playbook_path := Path(path)).is_file():
            if not validate_config(playbook_path, set(data.keys()) if data else set()):
                return 1

            bundle = make_bundle(playbook_path, playbook_path.parent)
            config = yaml.safe_load(playbook_path.read_bytes())

            settings: dict = config.get("settings", {})
            is_monitor = is_monitor or settings.get("cron") or settings.get("rate")
            settings.update(cli_settings)

            warn_settings(settings)

            if is_monitor:
                monitor_id = new_monitor(bundle, settings, secrets=data)
            else:
                ids = new_run(path=path, bundle=bundle, secrets=data, settings=settings)
        elif (base := Path(path)).is_dir():
            playbook_path = playbook or base / ".satori.yml"
            config = yaml.safe_load(playbook_path.read_bytes())

            settings: dict = config.get("settings", {})
            is_monitor = is_monitor or settings.get("cron") or settings.get("rate")
            settings.update(cli_settings)

            warn_settings(settings)

            if not validate_config(playbook_path, set(data.keys()) if data else set()):
                return 1

            bundle = make_bundle(playbook_path, playbook_path.parent)
            packet = make_packet(base)

            if missing_ymls(config, path):
                error_console.print(
                    "[warning]WARNING:[/] There are some .satori.yml outside the root "
                    "folder that have not been imported."
                )

            if is_monitor:
                monitor_id = new_monitor(bundle, settings, packet=packet, secrets=data)
            else:
                ids = new_run(
                    path=path,
                    bundle=bundle,
                    secrets=data,
                    packet=packet,
                    settings=settings,
                )
        else:
            error_console.print("ERROR: Invalid PATH")
            return 1

        if not is_monitor and not kwargs["json"]:
            for report_id in ids:
                console.print("Report ID:", report_id)
                console.print(
                    f"Report: https://satori.ci/report_details/?n={report_id}"
                )
        elif not is_monitor and kwargs["json"]:
            console.print_json(data={"ids": ids})
        elif is_monitor and not kwargs["json"]:
            console.print("Monitor ID:", monitor_id)
            console.print(f"Monitor: https://satori.ci/monitor?id={monitor_id}")
            return
        elif is_monitor and kwargs["json"]:
            console.print_json(data={"monitor_id": monitor_id})
            return

        if sync or report or output or files:
            wait(ids[0])

        ret = print_summary(ids[0], kwargs["json"]) if sync else 0

        if report:
            ReportCommand.print_report_asrt(ids[0], kwargs["json"])

        if output:
            print_output(ids[0], kwargs["json"])

        if files and config and has_files(config):
            download_files(ids[0])

        return ret
