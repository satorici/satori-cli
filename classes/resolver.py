import yaml
import os


def get_local_imports(playbook):
    obj = yaml.safe_load(playbook)
    ret: list[str] = obj.get("import", [])

    if not ret:
        return ret

    if not isinstance(ret, list) and not all(isinstance(i, str) for i in ret):
        raise Exception("Invalid imports")

    if any(i for i in ret if "\\" in i):
        raise Exception("Imports must use / as path separator")

    for ref in [i for i in ret if not i.startswith("satori://")]:
        if os.path.isfile(ref + ".yml"):
            continue
        else:
            raise Exception("Can't find local import")

    return ret
