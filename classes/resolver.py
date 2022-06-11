import yaml
import os


def get_local_imports(playbook, filename):
    imports = yaml.safe_load(playbook).get("import", [])
    path = os.path.dirname(filename)
    ret: list[str] = [
        os.path.join(path, i + ".yml") if not i.startswith("satori://")
        else "PLACEHOLDER" for i in imports
    ]

    if not ret:
        return ret

    if not isinstance(ret, list) and not all(isinstance(i, str) for i in ret):
        raise Exception("Invalid imports")

    if any(i for i in ret if "\\" in i):
        raise Exception("Imports must use / as path separator")

    for ref in ret:
        if ref == "PLACEHOLDER" or os.path.isfile(ref):
            continue
        else:
            raise Exception("Can't find local import")

    return ret
