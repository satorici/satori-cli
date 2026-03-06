import shutil
import subprocess
import sys
from argparse import ArgumentParser

from ..utils import error_console
from .base import BaseCommand

PROMPT = (
    "Check if all the github repositories from satorici are downloaded: "
    "playbooks, playbook-validator, satori-cli, satori-docs. "
    "If they are not downloaded do it. "
    "Help Satori's user to build a playbook. "
)


class AiCommand(BaseCommand):
    name = "ai"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("prompt", metavar="PROMPT", help="Describe the playbook you want")

    def __call__(self, prompt: str, **kwargs):
        if not shutil.which("claude"):
            error_console.print("ERROR: claude CLI is not installed.")
            error_console.print("Install it: npm install -g @anthropic-ai/claude-code")
            return 1

        full_prompt = PROMPT + prompt
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", full_prompt],
            check=False,
        )
        return result.returncode
