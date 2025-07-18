import json
import os
import shutil
import sys
import tempfile
import time
import uuid
import warnings
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Literal, Optional, Union, get_args

import httpx
import yaml
from rich.progress import open as progress_open
from satorici.validator import validate_settings

from satoricli.api import client
from satoricli.bundler import make_bundle
from satoricli.validations import get_parameters, validate_parameters

from ..utils import (
    console,
    detect_boolean,
    download_files,
    error_console,
    load_cli_params,
    missing_ymls,
    print_output,
    print_summary,
    tuple_to_dict,
    validate_config,
    wait,
)
from .base import BaseCommand
from .report import ReportCommand

VISIBILITY_VALUES = Literal["public", "private", "unlisted"]


def include_files(include: list[str]) -> Optional[str]:
    if not include:
        return
    temp_dir = Path(tempfile.gettempdir(), str(uuid.uuid4()))
    os.makedirs(temp_dir, exist_ok=True)
    for file in include:
        shutil.copy(file, temp_dir)
    shutil.make_archive(str(temp_dir), "gztar", temp_dir)
    return f"{temp_dir}.tar.gz"


def make_packet(path: str):
    temp_file = Path(tempfile.gettempdir(), str(uuid.uuid4()))
    shutil.make_archive(str(temp_file), "gztar", path)
    return f"{temp_file}.tar.gz"


def new_run(
    *,
    path: str,
    team: str,
    modes: Optional[dict] = None,
    bundle: Optional[Any] = None,
    packet: Optional[Path] = None,
    secrets: Optional[dict] = None,
    settings: Optional[dict] = None,
    save_report: Union[str, bool, None] = None,
    save_output: Union[str, bool, None] = None,
    params: Union[str, None] = None,
    visibility: Optional[VISIBILITY_VALUES] = None,
    clone: Optional[str] = None,
) -> list[str]:
    data = client.post(
        "/runs",
        data={
            "path": path,
            "secrets": json.dumps(secrets) if secrets else None,
            "settings": json.dumps(settings) if settings else None,
            "with_files": bool(packet),
            "modes": json.dumps(modes) if modes else None,
            "save_report": save_report,
            "save_output": save_output,
            "team": team,
            "run_params": " ".join(sys.argv[1:]),
            "visibility": visibility.capitalize() if visibility else None,
            "clone": clone,
        },
        files={"bundle": bundle} if bundle else {"": ""},
    ).json()

    if arc := data["upload_data"]:
        if arc.get("type") == "scan":
            reports_list = []
            while not reports_list:
                res = client.get(f"/scan/{data['report_ids'][0]}/reports").json()
                reports_list = res.get("rows")
                time.sleep(1)
            return [x["id"] for x in reports_list]
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
    team: str,
    *,
    packet: Optional[Path] = None,
    secrets: Optional[dict] = None,
    visibility: Optional[VISIBILITY_VALUES] = None,
) -> str:
    data = client.post(
        "/monitors",
        data={
            "secrets": json.dumps(secrets) if secrets else None,
            "settings": json.dumps(settings),
            "with_files": bool(packet),
            "team": team,
            "visibility": visibility.capitalize() if visibility else "Private",
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
    keys = (
        "cpu",
        "memory",
        "cron",
        "rate",
        "count",
        "name",
        "timeout",
        "os",
        "image",
        "storage",
    )

    return {key: value for key, value in args.items() if key in keys and value}


def warn_settings(settings: dict):
    with warnings.catch_warnings(record=True) as ws:
        validate_settings(settings)

        for w in ws:
            error_console.print("[warning]WARNING:[/]", w.message)


def get_parameters_from_env(playbook_path: str):
    with open(playbook_path) as f:
        playbook: dict = yaml.safe_load(f)
    return {k: [v] for k, v in os.environ.items() if k in get_parameters(playbook)}


class RunCommand(BaseCommand):
    name = "run"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("path", metavar="PATH")
        parser.add_argument(
            "-d", "--data", type=load_cli_params, action="append", default=[]
        )
        parser.add_argument(
            "-p",
            "--playbook",
            help="if PATH is a directory this playbook will be used",
        )
        parser.add_argument("--save-report", type=str, default=None)
        parser.add_argument("--save-output", type=str, default=None)
        parser.add_argument("--clone", type=str, default=None)
        parser.add_argument(
            "-df", "--data-file", type=load_cli_params, action="append", default=[]
        )
        parser.add_argument(
            "-i", "--include", dest="include_list", action="append", default=[]
        )

        settings = parser.add_argument_group("run settings")
        monitor = settings.add_mutually_exclusive_group()
        monitor.add_argument("--rate")
        monitor.add_argument("--cron")
        settings.add_argument("--name")
        settings.add_argument("--count", type=int)
        settings.add_argument("--cpu", type=int)
        settings.add_argument("--memory", type=int)
        settings.add_argument("--storage", type=int)
        settings.add_argument("--timeout", type=int)
        settings.add_argument("--os", choices=("windows", "linux"))
        settings.add_argument("--image")

        sync = parser.add_argument_group("sync run")
        sync.add_argument("-s", "--sync", action="store_true")
        sync.add_argument("-o", "--output", action="store_true")
        sync.add_argument("-r", "--report", action="store_true")
        sync.add_argument("-f", "--files", action="store_true")
        parser.add_argument(
            "--visibility", choices=get_args(VISIBILITY_VALUES), default=None
        )
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
        path: str,
        sync: bool,
        data: list[tuple[str, str]],
        data_file: list[tuple[str, str]],
        include_list: list,
        save_report: Union[str, bool, None],
        save_output: Union[str, bool, None],
        playbook: Optional[str],
        output: bool,
        report: bool,
        files: bool,
        team: str,
        filter_tests: list,
        text_format: Literal["plain", "md"],
        visibility: Optional[VISIBILITY_VALUES] = None,
        clone: Optional[str] = None,
        **kwargs,
    ):
        for file in data_file:
            data.append((file[0], f"read({file[1]})"))
            include_list.append(file[1])
        if save_report:
            temp_report = detect_boolean(save_report)
            save_report = save_report if temp_report is None else temp_report
        if save_output:
            save_output = detect_boolean(save_output)
        modes = {"sync": sync, "output": output, "report": report}

        parsed_data = tuple_to_dict(data) if data else None
        if parsed_data and not validate_parameters(parsed_data):
            raise ValueError("Malformed parameters")

        cli_settings = get_cli_settings(kwargs)
        is_monitor = bool(cli_settings.get("rate") or cli_settings.get("cron"))

        if playbook and "://" not in playbook and not os.path.isfile(playbook):
            error_console.print("ERROR: Invalid playbook arg.")
            return 1

        if "://" in path:
            with warnings.catch_warnings(record=True):
                validate_settings(cli_settings)
            ids = new_run(
                path=path,
                team=team,
                modes=modes,
                secrets=parsed_data,
                settings=cli_settings,
                save_report=save_report,
                save_output=save_output,
                visibility=visibility,
                clone=clone,
                packet=include_files(include_list),
            )

            is_monitor = False
            monitor_id = None
        elif (file_path := Path(path)).is_file():
            # HOOK HERE
            provided_var_names = set(parsed_data.keys()) if parsed_data else set()
            env_vars = get_parameters_from_env(file_path)

            if not validate_config(file_path, set(env_vars) | provided_var_names):
                return 1

            bundle = make_bundle(file_path, file_path.parent)
            config = yaml.safe_load(file_path.read_bytes())

            settings: dict = config.get("settings", {})
            is_monitor = is_monitor or settings.get("cron") or settings.get("rate")
            settings.update(cli_settings)

            warn_settings(settings)

            secrets = env_vars | (parsed_data or {})

            if is_monitor:
                monitor_id = new_monitor(
                    bundle, settings, team, secrets=secrets, visibility=visibility
                )
            else:
                ids = new_run(
                    path=path,
                    team=team,
                    modes=modes,
                    bundle=bundle,
                    secrets=secrets,
                    settings=settings,
                    save_report=save_report,
                    save_output=save_output,
                    visibility=visibility,
                    clone=clone,
                    packet=include_files(include_list),
                )
        elif (base := Path(path)).is_dir():
            settings = {}
            packet = make_packet(base)
            bundle = None
            secrets = None

            if playbook and "://" in playbook:
                playbook_path = playbook
            else:
                if playbook and os.path.isfile(playbook):
                    dir_playbook = Path(playbook)
                elif (base / ".satori.yml").is_file():
                    dir_playbook = base / ".satori.yml"
                else:
                    error_console.print("ERROR: No playbook found.")
                    return 1

                playbook_path = str(dir_playbook)

                config = yaml.safe_load(dir_playbook.read_bytes())

                settings: dict = config.get("settings", {})
                is_monitor = is_monitor or settings.get("cron") or settings.get("rate")
                settings.update(cli_settings)

                warn_settings(settings)

                provided_var_names = set(parsed_data.keys()) if parsed_data else set()
                env_vars = get_parameters_from_env(playbook_path)

                # HOOK HERE
                if not validate_config(
                    dir_playbook, set(env_vars) | provided_var_names
                ):
                    return 1

                if missing_ymls(config, path):
                    error_console.print(
                        "[warning]WARNING:[/] There are some .satori.yml outside the root "
                        "folder that have not been imported."
                    )

                bundle = make_bundle(dir_playbook, dir_playbook.parent)

                secrets = env_vars | (parsed_data or {})

            if is_monitor:
                monitor_id = new_monitor(
                    bundle,
                    settings,
                    team,
                    packet=packet,
                    secrets=secrets,
                    visibility=visibility,
                )
            else:
                ids = new_run(
                    path=playbook_path,
                    team=team,
                    modes=modes,
                    bundle=bundle,
                    secrets=secrets,
                    packet=packet,
                    settings=settings,
                    save_report=save_report,
                    save_output=save_output,
                    visibility=visibility,
                    clone=clone,
                )
        else:
            error_console.print("ERROR: Invalid PATH")
            return 1

        if not is_monitor and not kwargs["json"]:
            for report_id in ids:
                console.print("Report ID:", report_id)
                console.print(f"Report: https://satori.ci/report/{report_id}")
        elif not is_monitor and kwargs["json"]:
            console.print_json(data={"ids": ids})
        elif is_monitor and not kwargs["json"]:
            console.print("Monitor ID:", monitor_id)
            console.print(f"Monitor: https://satori.ci/monitor/{monitor_id}")
            return
        elif is_monitor and kwargs["json"]:
            console.print_json(data={"monitor_id": monitor_id})
            return

        if sync or report or output or files:
            wait(ids[0], output, filter_tests, text_format)

        ret = print_summary(ids[0], kwargs["json"]) if sync else 0

        if report:
            ReportCommand.print_report_asrt(ids[0], kwargs["json"])

        if output and kwargs["json"]:
            print_output(ids[0], kwargs["json"])

        if files:
            download_files(ids[0])

        return ret
