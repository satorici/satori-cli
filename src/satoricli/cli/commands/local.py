import json
import os
import platform
import re
import sys
import time
from argparse import ArgumentParser
from dataclasses import asdict
from pathlib import Path
from typing import Literal, Optional, Union, get_args

import httpx
import yaml
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from satori_runner import run

from satoricli.api import client
from satoricli.bundler import make_bundle
from satoricli.cli.commands.report import ReportCommand
from satoricli.validations import validate_parameters

from ..utils import (
    console,
    detect_boolean,
    error_console,
    load_cli_params,
    missing_ymls,
    output_to_string,
    print_output,
    print_summary,
    tuple_to_dict,
    validate_config,
)
from .base import BaseCommand

IS_LINUX = platform.system() == "Linux"
VISIBILITY_VALUES = Literal["public", "private", "unlisted"]
FUNCTIONS_RE = re.compile(r"(read|trim|strip)\((.+)\)")
FUNCTIONS_SUB_RE = re.compile(r"(.+)\${{(.+)}}(.+)?")


def new_local_run(
    team: str,
    bundle=None,
    playbook_uri: Optional[str] = None,
    secrets: Optional[dict] = None,
    name: Optional[str] = None,
    visibility: Optional[VISIBILITY_VALUES] = None,
) -> dict:
    """
    Create a new local run.

    Returns:
        dict: The response from the API. {"report_id":"<id>","recipe":"<url>","token":"Bearer <token>"}
    """
    return client.post(
        "/runs/local",
        data={
            "secrets": json.dumps(secrets) if secrets else None,
            "playbook_uri": playbook_uri,
            "name": name,
            "team": team,
            "run_params": " ".join(sys.argv[1:]),
            "visibility": visibility.capitalize() if visibility else None,
        },
        files={"bundle": bundle} if bundle else {"": ""},
    ).json()


def replace_variables(
    value: Union[str, list[str]], testcase: dict[str, str]
) -> Union[list, bytes, str]:
    if isinstance(value, str):
        for param_key, param_value in testcase.items():
            if m := FUNCTIONS_RE.search(param_value):
                value = execute_functions(value, m.group(1), m.group(2))
            else:
                value = replace_params(value, param_key, param_value)
        return value.encode(errors="ignore") if IS_LINUX else value
    else:
        for param_key, param_value in testcase.items():
            if m := FUNCTIONS_RE.search(param_value):
                # Run as shell if satori function is used
                value = execute_functions(" ".join(value), m.group(1), m.group(2))
                return value.encode(errors="ignore") if IS_LINUX else value
            for i, arg in enumerate(value):
                value[i] = replace_params(arg, param_key, param_value)
        return [arg.encode(errors="ignore") for arg in value] if IS_LINUX else value


def replace_params(old: str, secret_id: str, secret_value: str) -> str:
    return old.replace("${{" + secret_id + "}}", secret_value)


def execute_functions(original: str, function: str, param: str) -> str:
    if function == "read":
        return FUNCTIONS_SUB_RE.sub(f"cat {param} | xargs -IX \\1X\\3", original)
    else:
        return original


class LocalCommand(BaseCommand):
    name = "local"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("target", metavar="TARGET")
        parser.add_argument(
            "-p",
            "--playbook",
            help="if TARGET is a directory this playbook will be used",
        )
        parser.add_argument(
            "-d", "--data", type=load_cli_params, action="append", default=[]
        )
        parser.add_argument("--report", action="store_true")
        parser.add_argument("--output", action="store_true")
        parser.add_argument("-s", "--sync", action="store_true", help="Summary")
        parser.add_argument("--name", type=str)
        parser.add_argument("--save-report", type=str, default=None)
        parser.add_argument("--save-output", type=str, default=None)
        parser.add_argument(
            "--visibility", choices=get_args(VISIBILITY_VALUES), default=None
        )
        parser.add_argument(
            "-df", "--data-file", type=load_cli_params, action="append", default=[]
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
        target: str,
        data: list[tuple[str, str]],
        data_file: list[tuple[str, str]],
        playbook: Optional[str],
        report: bool,
        output: bool,
        sync: bool,
        name: str,
        team: str,
        save_report: Union[str, bool, None],
        save_output: Union[str, bool, None],
        visibility: Optional[VISIBILITY_VALUES],
        filter_tests: list,
        text_format: Literal["plain", "md"],
        **kwargs,
    ):
        for file in data_file:
            data.append((file[0], f"read({file[1]})"))
        parsed_data = tuple_to_dict(data) if data else None
        if parsed_data and not validate_parameters(parsed_data):
            raise ValueError("Malformed parameters")

        workdir = Path(target) if os.path.isdir(target) else Path()
        config = None

        if (playbook and "://" in playbook) or "://" in target:
            bundle = None
        elif (playbook and os.path.isfile(playbook)) or os.path.isfile(target):
            path = Path(playbook or target)
            config = yaml.safe_load(path.read_bytes())

            if not validate_config(
                path, set(parsed_data.keys()) if parsed_data else set()
            ):
                return 1

            bundle = make_bundle(path, path.parent)
        elif os.path.isdir(target):
            playbook_path = workdir / ".satori.yml"
            config = yaml.safe_load(playbook_path.read_bytes())

            if not validate_config(
                playbook_path, set(parsed_data.keys()) if parsed_data else set()
            ):
                return 1

            bundle = make_bundle(playbook_path, playbook_path.parent)

            if missing_ymls(config, workdir):
                error_console.print(
                    "[warning]WARNING:[/] There are some .satori.yml outside the root "
                    "folder that have not been imported."
                )
        else:
            error_console.print("ERROR: Invalid args")
            return 1

        local_run = new_local_run(
            team,
            bundle,
            secrets=parsed_data,
            name=name,
            visibility=visibility,
            playbook_uri=playbook or target,
        )

        save_output_setting = True
        save_report_setting = True
        if config and config.get("settings"):
            if config["settings"].get("saveOutput") is not None:
                save_output_setting = config["settings"]["saveOutput"]
            if config["settings"].get("saveReport") is not None:
                save_report_setting = config["settings"]["saveReport"]
        save_output = (
            detect_boolean(save_output) if save_output else save_output_setting
        )
        save_report = (
            detect_boolean(save_report) if save_report else save_report_setting
        )

        report_id = local_run["report_id"]

        if not kwargs["json"]:
            console.print("Report ID:", report_id)
            console.print(f"Report: https://satori.ci/report/{report_id}")
        elif kwargs["json"]:
            console.print_json(data={"report_id": report_id})

        with (
            httpx.stream("GET", local_run["recipe"]) as s,
            Progress(
                SpinnerColumn("dots2"),
                TextColumn("[progress.description]Status: {task.description}"),
                TimeElapsedColumn(),
                console=error_console,
            ) as progress,
        ):
            os.chdir(workdir)
            task = progress.add_task("Starting execution")
            start_time = time.monotonic()

            headers = {"Authorization": "Bearer " + local_run["token"]}

            for line in s.iter_lines():
                message: dict = json.loads(line)
                progress.update(task, description="Running [b]" + message["path"])
                args = replace_variables(message["value"], message["testcase"])
                out = run(args, message.get("settings", {}).get("setCommandTimeout"))
                output_dict = asdict(out)
                output_dict["stdout"] = output_to_string(out.stdout)
                output_dict["stderr"] = output_to_string(out.stderr)
                output_dict["os_error"] = output_to_string(out.os_error)
                result = {
                    "path": message.pop("path"),
                    **output_dict,
                    "command": message,
                }
                client.post("outputs/upload", json=result, headers=headers)

            client.put(
                "/runs/local/upload",
                params={
                    "run_time": time.monotonic() - start_time,
                    "save_report": save_report,
                    "save_output": save_output,
                },
                headers=headers,
            )
            progress.update(task, description="Completed")

        if sync:
            print_summary(report_id, kwargs["json"])

        if report:
            ReportCommand.print_report_asrt(report_id, kwargs["json"])

        if output:
            print_output(report_id, kwargs["json"], filter_tests, text_format)

        report_data = client.get(f"/reports/{report_id}").json()
        return 0 if report_data["fails"] == 0 else 1
