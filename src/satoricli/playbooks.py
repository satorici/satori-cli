import os
from pathlib import Path
from typing import Optional

import yaml

from .cli.utils import autosyntax, autotable, console
from .validations import get_parameters


def clone(directoryName: Path):
    """Clone or pull the playbooks repo"""

    try:
        import git
    except ImportError:
        print(
            "The git package could not be imported.",
            "Please make sure that git is installed in your system.",
        )
        return 1

    if directoryName.is_dir():
        repo = git.Repo(directoryName)
        repo.branches["main"].checkout(force=True)
        repo.remote().pull()
        print("Satori Playbooks repo updated to latest vesrsion")
    else:
        git.Repo.clone_from("https://github.com/satorici/playbooks.git", directoryName)
        print("Satori Playbooks repo clone started")
    return 0


def file_finder(directoryName) -> list[dict]:
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


def display_public_playbooks(playbook_id: Optional[str] = None) -> None:
    directoryName = Path.home() / ".satori/playbooks"

    if clone(directoryName) == 0:
        playbooks = file_finder(directoryName)
        playbooks.sort(key=lambda x: x["filename"])

        if not playbook_id:  # satori playbook --public
            # Print table with playbooks data by default
            autotable(playbooks)
        else:  # satori playbook satori://x
            # print the content of a playbook
            playbook_path = None
            for playbook in playbooks:
                if playbook["filename"] == playbook_id:
                    playbook_path = Path(
                        str(directoryName)
                        + playbook["filename"].replace("satori://", "/")
                    )
                    autosyntax(playbook_path.read_text(), lexer="YAML")
                    break
            if playbook_path is None:
                console.print("[red]Playbook not found")
