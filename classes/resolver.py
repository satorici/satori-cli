import os
import re

import yaml


IMPORT_REGEX = re.compile(r"^file:\/\/\/?(\w\/?)+\.(ya?ml)$")


def is_import(value):
    return isinstance(value, list) and (
        all(isinstance(e, str) and IMPORT_REGEX.fullmatch(e) for e in value)
    )


def get_local_files(config: dict):
    paths = set()
    for value in config.values():
        if is_import(value):
            paths.update(p[7:] for p in value)
        elif isinstance(value, dict):
            paths.update(get_local_files(value))
    return paths


def get_local_imports(stream, dir):
    file_list = get_local_files(yaml.safe_load(stream))

    for path in file_list:
        if not os.path.isfile(os.path.join(dir, path)):
            raise Exception(f"{path} is not a file")

    return file_list
