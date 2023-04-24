import re

from flatdict import FlatDict

INPUT_REGEX = re.compile(r"\$\(([\w-]+)\)")


def is_command_block(value):
    if isinstance(value, list):
        if all(
            (
                isinstance(v, list) and len(v) == 1 and isinstance(v[0], str)
                for v in value
            )
        ):
            return True


def get_unbound(commands: list[list[str]], key: str, flat_config: dict[str]):
    variables = set()

    for command in commands:
        variables.update(INPUT_REGEX.findall(command[0]))

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
        if is_command_block(value):
            parameters.update(get_unbound(value, key, flat_config))

    return parameters
