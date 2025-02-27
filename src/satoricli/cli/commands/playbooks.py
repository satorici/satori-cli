from argparse import ArgumentParser
from typing import Optional
import shutil

from satoricli.api import client
from satoricli.cli.utils import autoformat, autotable

from ..utils import BootstrapTable, console, get_offset
from .base import BaseCommand


class PlaybooksCommand(BaseCommand):
    name = "playbooks"

    @staticmethod
    def truncate_image_name(image_name: str, max_length: int = 20) -> str:
        """Truncate image name to specified length, adding ... if necessary"""
        if len(image_name) <= max_length:
            return image_name.ljust(max_length)
        return image_name[:max_length-3] + "..."

    @staticmethod
    def calculate_widths(sast_rows, dast_rows):
        """Calculate widths ensuring URI and Parameters are never truncated"""
        terminal_width = shutil.get_terminal_size().columns
        
        all_rows = sast_rows + dast_rows
        uri_width = max(len(row["uri"]) for row in all_rows)
        
        max_params_length = 0
        if dast_rows:
            max_params_length = max(len("\n".join(row.get("parameters", []))) for row in dast_rows)
        
        MIN_IMAGE_WIDTH = 15
        MIN_NAME_WIDTH = 10
        
        BORDER_PADDING = 3
        SAST_PADDING = BORDER_PADDING * 3
        DAST_PADDING = BORDER_PADDING * 4
        
        available_width = terminal_width - uri_width - max_params_length - max(SAST_PADDING, DAST_PADDING)
        
        if available_width < 0:
            image_width = MIN_IMAGE_WIDTH
            name_width = max(MIN_NAME_WIDTH, terminal_width - uri_width - max_params_length - DAST_PADDING - image_width)
        else:
            image_width = max(MIN_IMAGE_WIDTH, available_width // 3)
            name_width = max(MIN_NAME_WIDTH, available_width - image_width)
        
        sast_name_width = name_width + max_params_length
        
        return {
            'sast': (uri_width, sast_name_width, image_width),
            'dast': (uri_width, name_width, max_params_length, image_width)
        }

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "-p",
            "--page",
            dest="page",
            type=int,
            default=1,
            help="Playbooks page number",
        )
        parser.add_argument(
            "-l",
            "--limit",
            dest="limit",
            type=int,
            default=20,
            help="Page limit number",
        )
        parser.add_argument(
            "--public", action="store_true", help="Fetch public satori playbooks"
        )
        parser.add_argument("--monitor", help="A bool value")

    def __call__(
        self, page: int, limit: int, public: bool, monitor: Optional[str], **kwargs
    ):
        offset = get_offset(page, limit)
        params: dict = {"offset": offset, "limit": limit}
        if public:
            data = client.get("/playbooks/public", params=params).json()
            data["rows"] = [row for row in data["rows"] if row["uri"] != "satori://.satori.yml"]
        else:
            if monitor:
                params["monitor"] = monitor
            data = client.get("/playbooks", params=params).json()

        if public and not kwargs["json"]:
            sast_list = list(filter(lambda x: not bool(x.get("parameters")), data["rows"]))
            dast_list = list(filter(lambda x: bool(x.get("parameters")), data["rows"]))
            
            widths = self.calculate_widths(sast_list, dast_list)
            
            console.rule("SAST")
            autotable(
                [
                    {
                        "uri": x["uri"], 
                        "name": x["name"][:widths['sast'][1]] + "..." if len(x["name"]) > widths['sast'][1] else x["name"], 
                        "image": self.truncate_image_name(x["image"], widths['sast'][2])
                    }
                    for x in sast_list
                ],
                widths=widths['sast']
            )
            
            console.rule("DAST")
            autotable(
                [
                    {
                        "uri": x["uri"],
                        "name": x["name"][:widths['dast'][1]] + "..." if len(x["name"]) > widths['dast'][1] else x["name"],
                        "parameters": "\n".join(x["parameters"]),  # Sin truncar
                        "image": self.truncate_image_name(x["image"], widths['dast'][3])
                    }
                    for x in dast_list
                ],
                widths=widths['dast']
            )
            
        elif kwargs["json"]:
            autoformat(data["rows"], jsonfmt=kwargs["json"], list_separator="-" * 48)
        else:
            autotable(BootstrapTable(**data), limit=limit, page=page, widths=(16,))