import shutil
import subprocess
from argparse import ArgumentParser
from pathlib import Path

from ..utils import error_console
from .base import BaseCommand

PROMPT_FILE = Path(__file__).parent / "satori_skill.md"


class AiCommand(BaseCommand):
    name = "ai"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument(
            "prompt",
            metavar="PROMPT",
            nargs="?",
            default=None,
            help="Optional initial prompt (omit for interactive mode)",
        )

    def __call__(self, prompt: str | None = None, **kwargs):
        if not shutil.which("claude"):
            error_console.print("ERROR: claude CLI is not installed.")
            error_console.print("Install it: npm install -g @anthropic-ai/claude-code")
            return 1

        prompt_text = PROMPT_FILE.read_text(encoding="utf-8")

        cmd = ["claude", "--dangerously-skip-permissions", "--system-prompt", prompt_text]
        if prompt:
            cmd += ["-p", prompt]

        result = subprocess.run(cmd, check=False)
        return result.returncode
