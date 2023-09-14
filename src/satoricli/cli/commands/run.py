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
from satoricli.cli.utils import autoformat, check_monitor, console, format_outputs
from satoricli.utils import load_config
from satoricli.validations import get_parameters, has_executions, validate_parameters

from .base import BaseCommand


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

        target = Path(path)
        params = set()

        if data:
            if not validate_parameters(data):
                raise ValueError("Malformed parameters")

            params.update(data.keys())
            data = str(data)  # TODO: Modify API to receive JSON

        if path.startswith("satori://"):
            exec_data = self.run_url(path, data, **kwargs)

            if (sync or output or report or files) and exec_data:
                return self.run_sync(exec_data, output, report, files, **kwargs)

        if target.is_dir() and (target / ".satori.yml").is_file():
            playbook = target / ".satori.yml"
        elif target.is_file():
            playbook = target
        else:
            console.print("[error]Playbook file or folder not found")
            return 1

        try:
            config = yaml.safe_load(playbook.read_text())
        except yaml.YAMLError as e:
            console.print(f"Error parsing the playbook [bold]{playbook.name}[/]:\n", e)
            return 1

        try:
            with warnings.catch_warnings(record=True) as w:
                validate_playbook(config)

            for warning in w:
                if warning.category == NoLogMonitorWarning:
                    console.print(
                        "[warning]WARNING:[/] No notifications (log, onLogFail or "
                        "onLogPass) were defined for the Monitor"
                    )
        except TypeError:
            console.print("Error: playbook must be a mapping type")
            return 1
        except (PlaybookVariableError, NoExecutionsError):
            pass
        except PlaybookValidationError as e:
            console.print(
                f"Validation error on playbook [bold]{playbook.name}[/]:\n", e
            )
            return 1

        if not has_executions(config, playbook.parent):
            console.print("[error]No executions found")
            return 1

        variables = get_parameters(config)

        if variables - params:
            console.print(f"[error]Required parameters: {variables - params}")
            return 1

        if target.is_dir():
            exec_data = self.run_folder(path, data)
        else:  # is file
            exec_data = self.run_file(path, data)

        if (sync or output or report or files) and exec_data:
            return self.run_sync(exec_data, output, report, files, **kwargs)

    def run_file(self, path: str, data: Optional[dict]):
        bundle = make_bundle(path)
        is_monitor = check_monitor(path)
        url = client.post(
            "/runs/bundle", json={"secrets": data or "", "is_monitor": is_monitor}
        ).json()
        res = httpx.post(  # nosec
            url["url"], data=url["fields"], files={"file": bundle}, timeout=None
        )
        res.raise_for_status()

        if is_monitor:
            exec_type = "monitor"
            exec_id = url["monitor"]
            console.print(f"Monitor ID: {exec_id}")
            console.print(f"Status: https://www.satori-ci.com/status?id={exec_id}")
        else:
            exec_type = "report"
            exec_id = url["report_id"]
            console.print(f"Report ID: {exec_id}")
            console.print(
                f"Report: https://www.satori-ci.com/report_details/?n={exec_id}"
            )

        return {"type": exec_type, "id": exec_id}

    def run_folder(self, path: str, data: dict):
        """Upload directory and run"""
        satori_yml = Path(path, ".satori.yml")
        bundle = make_bundle(str(satori_yml), from_dir=True)
        is_monitor = check_monitor(satori_yml)
        temp_file = Path(tempfile.gettempdir(), str(uuid.uuid4()))
        full_path = f"{temp_file}.tar.gz"

        local_ymls = list(
            filter(lambda p: p.is_file(), Path(path).rglob(".satori.yml"))
        )

        imported = get_local_files(yaml.safe_load(satori_yml.read_text()))["imports"]

        if len(local_ymls) > 1 and len(local_ymls) - 1 > len(imported):
            console.print(
                "[warning]WARNING:[/] There are some .satori.yml outside the root "
                "folder that have not been imported."
            )

        shutil.make_archive(str(temp_file), "gztar", path)

        res = client.post(
            "/runs/archive", json={"secrets": data or "", "is_monitor": is_monitor}
        ).json()
        arc = res["archive"]
        bun = res["bundle"]
        mon = res["monitor"]
        report_id = res["report_id"]

        try:
            with progress_open(full_path, "rb", description="Uploading...") as f:
                res = httpx.post(arc["url"], data=arc["fields"], files={"file": f})
            res.raise_for_status()
        finally:
            os.remove(full_path)

        res = httpx.post(bun["url"], data=bun["fields"], files={"file": bundle})
        res.raise_for_status()

        if is_monitor:
            exec_type = "monitor"
            exec_id = mon
            console.print(f"Monitor ID: {mon}")
            console.print(f"Status: https://www.satori-ci.com/status?id={mon}")
        else:
            exec_type = "report"
            exec_id = report_id
            console.print(f"Report ID: {exec_id}")
            console.print(
                f"Report: https://www.satori-ci.com/report_details/?n={exec_id}"
            )
        return {"type": exec_type, "id": exec_id}

    def run_url(self, path: str, data: dict, **kwargs):
        info = client.post(
            "/runs/url", json={"secrets": data, "is_monitor": False, "url": path}
        ).json()
        autoformat(
            {"Running with the ID": info.get("report_id")}, jsonfmt=kwargs["json"]
        )
        return {"type": "report", "id": info["report_id"]}

    def run_sync(
        self, exec_data: dict, output: bool, report: bool, files: bool, **kwargs
    ):
        if exec_data["type"] == "monitor":
            console.print(
                "[warning]WARNING:[/] Sync mode is not supported for monitors"
            )
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]Status: {task.description}"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("Fetching data")
            status = "Unknown"

            while status not in ("Completed", "Undefined"):
                try:
                    report_data = client.get(f"/reports/{exec_data['id']}").json()
                    status = report_data.get("status", "Unknown")
                except httpx.HTTPStatusError as e:
                    if 400 <= e.response.status_code < 500:
                        status = "Unknown"
                    else:
                        return 1

                progress.update(task, description=status)
                time.sleep(1)

        if status == "Undefined":
            if comments := report_data.get("comments"):
                console.print(f"[error]Error: {comments}")
            return 1

        if not any((report, output, files)) and status == "Completed":
            fails = report_data["fails"]

            if isinstance(fails, int):
                console.print("Result:", "Pass" if not fails else f"Fail({fails})")

            return 0 if fails == 0 else 1

        if report:
            report_out = []
            # Remove keys
            json_data = report_data.get("report") or []
            for report in json_data:
                report.pop("gfx", None)
                report_out.append(report)
                asserts = []
                for asrt in report["asserts"]:
                    asrt.pop("count", None)
                    asrt.pop("description", None)
                    if len(asrt.get("data", [])) == 0:
                        asrt.pop("data", None)
                    asserts.append(asrt)
            autoformat(report_out, list_separator="- " * 20)
        elif output:
            r = client.get(f"/outputs/{exec_data['id']}")
            with httpx.stream("GET", r.json()["url"], timeout=300) as s:
                format_outputs(s.iter_lines())
        elif files:
            with client.stream(
                "GET", f"/reports/{exec_data['id']}/files", follow_redirects=True
            ) as s:
                total = int(s.headers["Content-Length"])

                with Progress() as progress:
                    task = progress.add_task("Downloading...", total=total)

                    with open(f"satorici-files-{exec_data['id']}.tar.gz", "wb") as f:
                        for chunk in s.iter_raw():
                            progress.update(task, advance=len(chunk))
                            f.write(chunk)
