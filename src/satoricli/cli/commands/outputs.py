from argparse import ArgumentParser
from datetime import date
from typing import Optional

import requests

from satoricli.api import HOST, client, configure_client
from satoricli.cli.utils import console, format_outputs
from satoricli.utils import load_config

from ..arguments import date_args
from .base import BaseCommand


class OutputsCommand(BaseCommand):
    name = "outputs"
    options = (date_args,)

    def register_args(self, parser: ArgumentParser):
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

    def __call__(
        self,
        raw: bool,
        name: Optional[str] = None,
        failed: Optional[bool] = None,
        to_date: Optional[date] = None,
        from_date: Optional[date] = None,
        **kwargs,
    ):
        config = load_config()[kwargs["profile"]]
        configure_client(config["token"])

        res = client.get(
            f"{HOST}/outputs",
            params={
                "from_date": from_date,
                "to_date": to_date,
                "name": name,
                "failed": failed,
            },
        )

        with requests.Session() as s:
            for item in res.json():
                output = s.get(item["url"], stream=True)

                if not output.ok:
                    continue

                if raw:
                    console.rule()
                    console.print(output.text)
                else:
                    console.print(f"Report: {item['report_id']}")
                    format_outputs(output.iter_lines())
                    console.print()
