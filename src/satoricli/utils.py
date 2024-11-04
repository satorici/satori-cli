from pathlib import Path

import yaml


def load_config(config_path=None):
    config = {}
    
    if config_path:
        path = Path(config_path)
        if path.is_file():
            path = path.parent
        locations = (path / ".satori_credentials.yml",)
    else:
        locations = (
            Path(".satori_credentials.yml"),
            Path.home() / ".satori_credentials.yml",
        )

    for location in locations:
        if not location.is_file():
            continue
        try:
            config.update(yaml.safe_load(location.read_text()))
        except yaml.YAMLError as e:
            raise Exception(f"Error parsing YAML from {location}: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading config from {location}: {str(e)}")

    if not config and config_path:
        paths_checked = "\n  - ".join(str(p) for p in locations)
        raise Exception(f"No valid configuration file found in the following locations:\n  - {paths_checked}")

    return config


def save_config(config: dict):  # TODO: Global/local config
    with (Path.home() / ".satori_credentials.yml").open("w") as f:
        f.write(yaml.safe_dump(config))
