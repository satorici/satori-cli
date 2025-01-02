from pathlib import Path

import yaml
from flatdict import FlatDict
from satorici.validator import (
    INPUT_REGEX,
    is_command_group,
    is_import_group,
    validate_playbook,
)
from satorici.validator.exceptions import NoExecutionsError, PlaybookVariableError


def get_unbound(commands: list[str], key: str, flat_config: dict[str]):
    variables = set()

    for command in commands:
        variables.update(INPUT_REGEX.findall(command))

    keys: list[str] = flat_config.keys()
    previous_paths = keys[: keys.index(key)]

    path = key.split(":")
    levels = len(path)

    for variable in variables:
        prefixes = tuple(":".join(path[:i] + [variable]) for i in range(levels))
        valid_prefixes = [path for path in previous_paths if path.startswith(prefixes)]

        if not valid_prefixes:
            yield variable


def get_parameters(config: dict):
    """Returns the needed parameters from the yaml loaded config"""

    flat_config = FlatDict(config)
    parameters: set[str] = set()

    for key, value in flat_config.items():
        if is_command_group(value):
            parameters.update(get_unbound(value, key, flat_config))

    return parameters


def validate_parameters(params: dict):
    if isinstance(params, dict):
        if all(isinstance(v, (str, int, list)) for v in params.values()):
            return True


def has_executions(config: dict, base_dir: Path):
    flat_config = FlatDict(config)
    imports: set[str] = set()

    for value in flat_config.values():
        if is_import_group(value):
            for i in value:
                if i.startswith("satori"):
                    return True

                imports.add(i)
        elif is_command_group(value):
            return True

    for i in imports:
        path = base_dir / i[7:]

        if not path.is_file():
            continue

        try:
            imported = yaml.safe_load((base_dir / i[7:]).read_text())
            validate_playbook(imported)
        except (PlaybookVariableError, NoExecutionsError):
            pass
        except Exception:
            continue

        for value in FlatDict(imported).values():
            if is_command_group(value):
                return True

    return False
