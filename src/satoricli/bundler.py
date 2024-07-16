import io
from pathlib import Path
from zipfile import ZipFile

import yaml
from satorici.validator import is_import_group, is_input_group, is_test


def get_local_files(config: dict):
    paths = {"imports": set(), "inputs": set()}
    for value in config.values():
        if is_import_group(value):
            paths["imports"].update([p[7:] for p in value if p.startswith("file")])
        elif is_input_group(value):
            paths["inputs"].update(
                [
                    p.get("file")
                    for p in value[0]
                    if isinstance(p, dict) and p.get("file")
                ]
            )
        elif is_test(value):
            subtest_files = get_local_files(value)
            paths["imports"].update(subtest_files["imports"])
            paths["inputs"].update(subtest_files["inputs"])
    return paths


def get_references(stream, dir):
    file_list = get_local_files(yaml.safe_load(stream))

    for key, files in file_list.items():
        for path in files:
            if not Path(dir, path).is_file():
                raise Exception(f"{key}: {path} is not a file")

    return file_list


def make_bundle(playbook: Path, base_dir: Path):
    obj = io.BytesIO()
    with open(playbook) as f, ZipFile(obj, "x") as zip_file:
        references = get_references(f.read(), base_dir)
        zip_file.write(playbook, ".satori.yml")
        for _key, paths in references.items():
            for path in paths:
                zip_file.write(base_dir / path, path)

    obj.seek(0)
    return obj
