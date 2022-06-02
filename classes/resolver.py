import yaml
import os


def get_local_imports(playbook):
    imports = yaml.safe_load(playbook).get("import", [])
    ret: list[str] = [i for i in imports if not i.startswith("satori://")]

    if not ret:
        return ret

    if not isinstance(ret, list) and not all(isinstance(i, str) for i in ret):
        raise Exception("Invalid imports")

    if any(i for i in ret if "\\" in i):
        raise Exception("Imports must use / as path separator")

    for ref in ret:
        if os.path.isfile(ref + ".yml"):
            continue
        else:
            raise Exception("Can't find local import")

    return ret
