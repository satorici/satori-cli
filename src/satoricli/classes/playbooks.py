import os
import sys
from pathlib import Path
from tempfile import gettempdir

try:
    import git
except ImportError:
    git = None
import yaml
from rich.console import Console
from rich.table import Table

from .validations import get_parameters


def clone(directoryName):
    """Clone or pull the playbooks repo"""
    if git is None:
        print("The git package could not be imported. Please make sure that git is installed in your system.")
        return 1
    if os.path.exists(directoryName):
        repo = git.Repo(directoryName)
        repo.remotes.origin.pull()
        print("Satori Playbooks repo updated to latest vesrsion")
    else:
        git.Repo.clone_from("https://github.com/satorici/playbooks.git", directoryName)
        print("Satori Playbooks repo clone started")
    return 0


def file_finder(directoryName):
    """File finder"""
    playbooks = []
    list_dirs = os.walk(directoryName)
    for root, dirs, files in list_dirs:
        dirs = ""
        for d in dirs:
            dirs += os.path.join(root, d)
        dirs_printed = False
        for f in files:
            if f.endswith(".yml") and f != ".satori.yml":
                if dirs_printed is False:
                    dirs_printed = True

                filenames = os.path.join(root, f)

                parameters = []
                with open(filenames) as file:
                    try:
                        parameters = get_parameters(yaml.safe_load(file))
                    except Exception:
                        pass

                names = get_playbook_name(filenames)
                playbooks.append(
                    {
                        "filename": filenames.replace(str(directoryName), "satori:/"),
                        "name": names,
                        "parameters": ", ".join(parameters),
                    }
                )
    return playbooks


def get_playbook_name(filename):
    """Function to load files desc in list"""
    playbook = ""
    with open(filename, "r") as file:
        try:
            playbook = yaml.safe_load(file)
        except yaml.YAMLError:
            pass
        if "settings" in playbook and "name" in playbook["settings"]:
            return playbook["settings"]["name"]
        else:
            return "None"


def display_public_playbooks():
    directoryName = Path(gettempdir(), "satori-public-playbooks")

    if clone(directoryName) == 0:
        playbooks = file_finder(directoryName)
        playbooks.sort(key=lambda x: x["filename"])

        rows = []
        for playbook in playbooks:
            rows.append(
                (
                    playbook["filename"],
                    playbook["name"],
                    playbook["parameters"],
                )
            )

        table = Table(title="Public playbooks")

        table.add_column("Filename", no_wrap=True)
        table.add_column("Name")
        table.add_column("Parameters", justify="right")

        for row in rows:
            table.add_row(*row)

        console = Console()
        console.print(table)
    sys.exit(0)
