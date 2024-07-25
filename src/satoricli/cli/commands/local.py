import json
import os
import platform
import time
from argparse import ArgumentParser
from base64 import b64decode, b64encode
from dataclasses import asdict
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Optional, Union

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
    error_console,
    missing_ymls,
    print_output,
    print_summary,
    validate_config,
)
from .base import BaseCommand

IS_LINUX = platform.system() == "Linux"


def new_local_run(
    bundle=None, playbook_uri: Optional[str] = None, secrets: Optional[dict] = None
) -> dict:
    return client.post(
        "/runs/local",
        data={
            "secrets": json.dumps(secrets) if secrets else None,
            "playbook_uri": playbook_uri,
        },
        files={"bundle": bundle} if bundle else {"": ""},
    ).json()


def replace_variables(
    value: Union[str, list[str]], testcase: dict[str, str]
) -> Union[list, bytes, str]:
    if isinstance(value, str):
        for secret_key, secret_value in testcase.items():
            value = replace_secrets(value, secret_key, secret_value)
        return value.encode(errors="ignore") if IS_LINUX else value
    else:
        for key, test_value in testcase.items():
            for i, arg in enumerate(value):
                value[i] = replace_secrets(arg, key, test_value)
        return [arg.encode(errors="ignore") for arg in value] if IS_LINUX else value


def replace_secrets(old: str, secret_id: str, secret_value: str) -> str:
    value = b64decode(secret_value).decode(errors="ignore")
    return old.replace("${{" + secret_id + "}}", value)


class BytesEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return b64encode(o).decode()
        return super().default(o)


class LocalCommand(BaseCommand):
    name = "local"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("target", metavar="TARGET")
        parser.add_argument(
            "-p",
            "--playbook",
            help="if TARGET is a directory this playbook will be used",
        )
        parser.add_argument("-d", "--data", type=json.loads)
        parser.add_argument("--report", action="store_true")
        parser.add_argument("--output", action="store_true")
        parser.add_argument("--summary", action="store_true")

    def __call__(
        self,
        target: str,
        data: Optional[dict],
        playbook: Optional[str],
        report: bool,
        output: bool,
        summary: bool,
        **kwargs,
    ):
        if data and not validate_parameters(data):
            raise ValueError("Malformed parameters")

        workdir = Path(target) if os.path.isdir(target) else Path()

        if (playbook and "://" in playbook) or "://" in target:
            local_run = new_local_run(playbook_uri=playbook or target, secrets=data)
        elif (playbook and os.path.isfile(playbook)) or os.path.isfile(target):
            path = Path(playbook or target)

            if not validate_config(path, set(data.keys()) if data else set()):
                return 1

            bundle = make_bundle(path, path.parent)
            local_run = new_local_run(bundle, secrets=data)
        elif os.path.isdir(target):
            playbook_path = workdir / ".satori.yml"
            config = yaml.safe_load(playbook_path.read_bytes())

            if not validate_config(playbook_path, set(data.keys()) if data else set()):
                return 1

            bundle = make_bundle(playbook_path, playbook_path.parent)

            if missing_ymls(config, workdir):
                error_console.print(
                    "[warning]WARNING:[/] There are some .satori.yml outside the root "
                    "folder that have not been imported."
                )

            local_run = new_local_run(bundle, secrets=data)
        else:
            error_console.print("ERROR: Invalid args")
            return 1

        report_id = local_run["report_id"]

        if not kwargs["json"]:
            console.print("Report ID:", report_id)
            console.print(f"Report: https://satori.ci/report_details/?n={report_id}")
        elif kwargs["json"]:
            console.print_json(data={"report_id": report_id})

        with (
            httpx.stream("GET", local_run["recipe"]) as s,
            SpooledTemporaryFile(4096) as results,
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

            for line in s.iter_lines():
                message: dict = json.loads(line)
                progress.update(task, description="Running [b]" + message["path"])
                args = replace_variables(message["value"], message["testcase"])
                out = run(args, message.get("settings", {}).get("setCommandTimeout"))
                message["output"] = asdict(out)
                results.write(f"{json.dumps(message, cls=BytesEncoder)}\n".encode())

            results.seek(0)
            client.put(
                f"/runs/local/{report_id}",
                files={"results": results},
                params={"run_time": time.monotonic() - start_time},
            )
            progress.update(task, description="Completed")

        if summary:
            print_summary(report_id, kwargs["json"])

        if report:
            ReportCommand.print_report_asrt(report_id, kwargs["json"])

        if output:
            print_output(report_id, kwargs["json"])
