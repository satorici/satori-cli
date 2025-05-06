import io
import os
import tarfile
from argparse import ArgumentParser
from datetime import date
from typing import Literal, Optional, get_args

import httpx

from satoricli.api import client
from satoricli.cli.utils import console, format_outputs

from ..arguments import date_args
from .base import BaseCommand

ACTIONS = Literal["show", "export"]
REPORT_VISIBILITY = Literal["public", "unlisted", "private"]
RESULTS = Literal["pass", "fail", "unknown"]
PLAYBOOK_TYPE = Literal["public", "private"]


def capitalize(s: Optional[str]) -> Optional[str]:
    return s.capitalize() if s else s


class OutputsCommand(BaseCommand):
    name = "outputs"
    options = (date_args,)

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "action",
            metavar="ACTION",
            choices=get_args(ACTIONS),
            nargs="?",
            default="show",
            help="action to perform",
        )
        parser.add_argument(
            "--raw", action="store_true", help="print without formatting"
        )
        parser.add_argument("-n", "--name", help="playbook name")
        parser.add_argument(
            "-f",
            "--failed",
            action="store_const",
            const=True,
            help="fetch only failed reports outputs",
        )
        parser.add_argument(
            "--playbook-type",
            choices=get_args(PLAYBOOK_TYPE),
            default="public",
            help="Filter by playbook type",
        )
        parser.add_argument(
            "--report-visibility",
            choices=get_args(REPORT_VISIBILITY),
            help="Filter by report visibility",
        )
        parser.add_argument(
            "--result",
            choices=get_args(RESULTS),
            help="Filter by report result",
        )
        # parser.add_argument(
        #     "--query", type=str, help="Filter by output string (support regex)"
        # )

    def __call__(
        self,
        action: ACTIONS,
        raw: bool,
        name: Optional[str] = None,
        failed: Optional[bool] = None,
        to_date: Optional[date] = None,
        from_date: Optional[date] = None,
        playbook_type: Literal[PLAYBOOK_TYPE] = "public",
        report_visibility: Optional[REPORT_VISIBILITY] = None,
        result: Optional[RESULTS] = None,
        # query: Optional[str] = None,
        **kwargs,
    ):
        if action == "show":
            res = client.get(
                "/outputs",
                params={
                    "from_date": from_date,
                    "to_date": to_date,
                    "name": name,
                    "failed": failed,
                },
            )

            with httpx.Client() as c:
                for item in res.json():
                    with c.stream("GET", item["url"]) as stream:
                        if not stream.is_success:
                            continue

                        if raw:
                            console.rule()
                            console.print(stream.text)
                        else:
                            console.print(f"Report: {item['report_id']}")
                            format_outputs(stream.iter_lines())
                            console.print()
        elif action == "export":
            res = client.get(
                "/outputs/export",
                params={
                    "playbook_type": capitalize(playbook_type),
                    "report_visibility": capitalize(report_visibility),
                    "result": capitalize(result),
                    # "query": query,
                },
            )

            # Save response
            extract_dir = name if name else "export"

            if raw:
                # Save to file
                with open(f"{extract_dir}.tar.gz", "wb") as f:
                    f.write(res.content)
                    console.print(
                        f"Successfully dowloaded outputs to [b]{extract_dir}.tar.gz[/]"
                    )
                return

            # Untar file
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir)
                console.print(f"Created directory: {extract_dir}")
            else:
                console.print(
                    f"[warning]Directory already exists: [b]{extract_dir}[/]"
                    "\nRemove it manually to avoid conflicts"
                )

            # Use io.BytesIO to treat the bytes as a file-like object
            with io.BytesIO(res.content) as tar_buffer:
                with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
                    tar.extractall(path=extract_dir, filter="data")
                console.print(
                    f"Successfully dowloaded outputs to folder [b]{extract_dir}"
                )

            # List all extracted files
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    console.print(os.path.join(root, file))
