import json
import os
import tarfile
from io import BytesIO
from zipfile import ZipFile

import httpx

from satoricli.api import client

from ..utils import console, error_console, wait


def run_script(
    path: str, team: str, visibility: str | None, show_stdout: bool, settings: dict
):
    with BytesIO() as bundle:
        with ZipFile(bundle, "x") as zf:
            zf.writestr(".satori.yml", f"cmd: [ sh '{os.path.basename(path)}' ]")

        bundle.seek(0)

        data = client.post(
            "/runs",
            data={
                "path": path,
                "with_files": True,
                "save_report": True,
                "save_output": True,
                "team": team,
                "visibility": visibility.upper() if visibility else None,
                "settings": json.dumps(settings),
            },
            files={"bundle": bundle},
        ).json()

    report_id = data["report_ids"][0]
    arc = data["upload_data"]

    error_console.print("Report ID:", report_id)
    error_console.print(f"Report: https://satori.ci/report/{report_id}")

    with BytesIO() as packet:
        with tarfile.open(fileobj=packet, mode="w:gz") as tf:
            info = tf.gettarinfo(path, os.path.basename(path))
            info.mode = 0o755

            with open(path, "rb") as script:
                tf.addfile(info, script)

        packet.seek(0)

        res = httpx.post(arc["url"], data=arc["fields"], files={"file": packet})
        res.raise_for_status()

    if show_stdout:
        wait(report_id)

        for output in client.get(f"/outputs/{report_id}").json():
            stdout = output.get("output", {}).get("stdout")

            if stdout is not None:
                console.out(stdout, highlight=False)
