from argparse import ArgumentParser

from satori_help import HelpApp, start_docs_server

from ..utils import console
from .base import BaseCommand


class HelpCommand(BaseCommand):
    name = "help"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("-w", "--web", action="store_true")

    def __call__(self, web: bool, **kwargs):
        if web:
            console.print("Docs server running on http://localhost:9090")
            try:
                start_docs_server()
            except KeyboardInterrupt:
                pass
        else:
            HelpApp().run()
