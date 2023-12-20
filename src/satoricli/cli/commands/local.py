import json
import os
import platform
from argparse import ArgumentParser
from base64 import b64decode, b64encode
from dataclasses import asdict
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Optional

import httpx
import yaml
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


def new_local_run(bundle, secrets: Optional[dict] = None) -> dict:
    return client.post(
        "/runs/local",
        data={"secrets": json.dumps(secrets)} if secrets else None,
        files={"bundle": bundle},
    ).json()


class BytesEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return b64encode(o).decode()
        return super().default(o)


class LocalCommand(BaseCommand):
    name = "local"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("path", metavar="PATH", type=Path)
        parser.add_argument("-d", "--data", type=json.loads)
        parser.add_argument(
            "-p",
            "--playbook",
            type=Path,
            help="if PATH is a directory this playbook will be used",
        )
        parser.add_argument("--report", action="store_true")
        parser.add_argument("--output", action="store_true")
        parser.add_argument("--summary", action="store_true")

    def __call__(
        self,
        path: Path,
        data: Optional[dict],
        playbook: Optional[Path],
        report: bool,
        output: bool,
        summary: bool,
        **kwargs,
    ):
        if data and not validate_parameters(data):
            raise ValueError("Malformed parameters")

        if path.is_file():
            if not validate_config(path, set(data.keys()) if data else set()):
                return 1

            bundle = make_bundle(path, path.parent)
            local_run = new_local_run(bundle, data)
        elif path.is_dir():
            playbook_path = playbook or path / ".satori.yml"
            config = yaml.safe_load(playbook_path.read_bytes())

            if not validate_config(playbook_path, set(data.keys()) if data else set()):
                return 1

            bundle = make_bundle(playbook_path, playbook_path.parent)

            if missing_ymls(config, path):
                error_console.print(
                    "[warning]WARNING:[/] There are some .satori.yml outside the root "
                    "folder that have not been imported."
                )

            local_run = new_local_run(bundle, data)
        else:
            error_console.print("ERROR: Invalid PATH")
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
        ):
            if path.is_dir():
                os.chdir(path)

            for line in s.iter_lines():
                message: dict = json.loads(line)
                command = message["command"]

                windows_host = platform.system() == "Windows"

                if isinstance(command, str):
                    dec = b64decode(command)
                    args = (dec.decode(errors="ignore")) if windows_host else dec
                elif isinstance(command, list):
                    args = [
                        b64decode(arg).decode(errors="ignore")
                        if windows_host
                        else b64decode(arg)
                        for arg in command
                    ]

                out = run(args, message.get("settings", {}).get("setCommandTimeout"))
                message["output"] = asdict(out)
                results.write(f"{json.dumps(message, cls=BytesEncoder)}\n".encode())

            results.seek(0)
            client.put(f"/runs/local/{report_id}", files={"results": results})

        if summary:
            print_summary(report_id, kwargs["json"])

        if report:
            ReportCommand.print_report_asrt(report_id, kwargs["json"])

        if output:
            print_output(report_id, kwargs["json"])
