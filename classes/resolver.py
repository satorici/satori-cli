import yaml
import os


def get_local_imports(playbook):
    obj = yaml.safe_load(playbook)
    ret: list[str] = obj.get("imports", [])

    if not isinstance(ret, list) and not all(isinstance(i, str) for i in ret):
        raise Exception("Invalid imports")

    for ref in [i for i in ret if not i.startswith("satori://")]:
        if not os.path.isfile(ref) or not os.path.isdir(ref):
            raise Exception("Can't find local import")

    return ret
