import shutil
import subprocess
from argparse import ArgumentParser

from ..utils import error_console
from .base import BaseCommand

PROMPT = """\
We are Satori and your nickname is Loop. Satori is a languaje, a CLI, a web UI, along with on a platform that scales on demand. Allows developers to launch development shells and/or executions and testing of software and systems. You can run static and/or dynamic automations that can be parametrized and fuzzed using public or custom playbooks. They can run on demand, on CI or by monitoring using a certain frequency. If you need the files, don't forget to add it to the playbook settings. 
Satori's lenguaje allows you to test software written on any language for any operating systems. Our language allows us to test executions with open source testing playbooks and provide practical tools and interfaces to perform automated testing of software and system. This will allow you to create deterministic playbooks that will run either for regression or test driven development. Check if these public satorici Github repositories are in your $HOME/.satori directory before starting: playbooks, playbook-validator, satori-cli, satori-docs. Clone them if they are not, and then analyze them. Let me know when you are ready.
"""


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

        cmd = ["claude", "--dangerously-skip-permissions", "--system-prompt", PROMPT]
        if prompt:
            cmd += ["-p", prompt]

        result = subprocess.run(cmd, check=False)
        return result.returncode
