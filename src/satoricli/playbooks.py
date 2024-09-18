from pathlib import Path
from typing import Optional

import yaml
from rich.markdown import Markdown
from rich.panel import Panel

from .cli.utils import autosyntax, autotable, console, remove_yaml_prop
from .validations import get_parameters

PLAYBOOKS_DIR = Path.home() / ".satori/playbooks"


def sync():
    """Clone or pull the playbooks repo"""

    try:
        import git
    except ImportError:
        print(
            "The git package could not be imported.",
            "Please make sure that git is installed in your system.",
        )
        return False

    if PLAYBOOKS_DIR.is_dir():
        repo = git.Repo(PLAYBOOKS_DIR)
        repo.branches["main"].checkout(force=True)
        repo.remote().pull()
        # print(
        #    "Satori playbooks' repo https://github.com/satorici/playbooks",
        #    "updated to latest version",
        # )
    else:
        git.Repo.clone_from("https://github.com/satorici/playbooks.git", PLAYBOOKS_DIR)
        # print("Satori Playbooks repo clone started")
    return True


def file_finder() -> list[dict]:
    playbooks = []

    for playbook in PLAYBOOKS_DIR.rglob("*.yml"):
        if ".github" in playbook.parts:
            continue

        try:
            parameters = get_parameters(yaml.safe_load(playbook.read_text()))
        except Exception:
            parameters = ()

        scheme = (
            yaml.safe_load(playbook.read_bytes())
            .get("settings", {})
            .get("scheme", "satori")
        )

        playbooks.append(
            {
                "uri": f"{scheme}://" + playbook.relative_to(PLAYBOOKS_DIR).as_posix(),
                "name": get_playbook_name(playbook),
                "parameters": ", ".join(parameters),
            }
        )

    return playbooks


def get_playbook_name(filename: Path):
    try:
        config = yaml.safe_load(filename.read_text())
        return config["settings"]["name"]
    except Exception:
        pass


def display_public_playbooks(
    playbook_id: Optional[str] = None, original: bool = False
) -> None:
    if not sync():
        return

    if not playbook_id:  # satori playbook --public
        playbooks = file_finder()
        playbooks.sort(key=lambda x: x["uri"])
        autotable(playbooks)
    else:  # satori playbook satori://x
        path = PLAYBOOKS_DIR / playbook_id.removeprefix("satori://")

        if path.is_file():
            text = path.read_text()
            if original:
                print(text)
                return
            loaded_yaml = yaml.safe_load(text)
            if description := loaded_yaml.get("settings", {}).get("description"):
                if name := loaded_yaml.get("settings", {}).get("name"):
                    description = f"## {name}\n{description}"
                mk = Markdown(description)
                console.print(Panel(mk))
            yml = remove_yaml_prop(text, "description")
            yml = remove_yaml_prop(yml, "name")
            autosyntax(yml, lexer="YAML")
        else:
            console.print("[red]Playbook not found")
