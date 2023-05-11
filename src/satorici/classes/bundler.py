import io
import os
import re
from pathlib import Path
from zipfile import ZipFile

import yaml


IMPORT_REGEX = re.compile(r"(satori|file):\/(\/[\w-]+)+\.ya?ml")


def is_import(value):
    return isinstance(value, list) and (
        all(isinstance(e, str) and IMPORT_REGEX.fullmatch(e) for e in value)
    )


def is_input(value):
    return isinstance(value, list) and (all(isinstance(e, (str, dict)) for e in value))


def get_local_files(config: dict):
    paths = {"imports": set(), "inputs": set()}
    for value in config.values():
        if is_import(value):
            paths["imports"].update([p[7:] for p in value if p.startswith("file")])
        elif is_input(value):
            paths["inputs"].update(
                [p.get("file") for p in value if isinstance(p, dict) and p.get("file")]
            )
        elif isinstance(value, dict):
            paths.update(get_local_files(value))
    return paths


def get_references(stream, dir):
    file_list = get_local_files(yaml.safe_load(stream))

    for key, files in file_list.items():
        for path in files:
            if not Path(dir, path).is_file():
                raise Exception(f"{key}: {path} is not a file")

    return file_list


def make_bundle(playbook: str, from_dir: bool = False):
    obj = io.BytesIO()
    with open(playbook) as f, ZipFile(obj, "x") as zip_file:
        playbook_dir = os.path.dirname(playbook)
        references = get_references(f.read(), playbook_dir)
        zip_file.write(playbook, ".satori.yml")
        if from_dir:
            zip_file.writestr(".fromupload", "")
        for key, paths in references.items():
            for path in paths:
                zip_file.write(Path(playbook_dir, path), Path(key, path))

    obj.seek(0)
    return obj
