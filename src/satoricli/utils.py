from pathlib import Path

import yaml


def load_config():
    config = {}

    locations = (
        Path(".satori_credentials.yml"),
        Path.home() / ".satori_credentials.yml",
    )

    for location in locations:
        if not location.is_file():
            continue

        config.update(yaml.safe_load(location.read_text()))

    return config


def save_config(config: dict):  # TODO: Global/local config
    with (Path.home() / ".satori_credentials.yml").open("w") as f:
        f.write(yaml.safe_dump(config))
