from typing import Union
import json
import yaml

__decorations = "▢•○░"


def get_decoration(indent):
    return "  " * indent + __decorations[indent % len(__decorations)] + " "


def dict_formatter(
    obj: dict, capitalize: bool = False, indent: int = 0, list_separator: str = None
):
    for key in obj.keys():
        indent_text = get_decoration(indent)
        key_text = key.capitalize() if capitalize else key
        if isinstance(obj[key], dict):
            print(indent_text + f"{key_text}:")
            dict_formatter(obj[key], capitalize, indent + 1)
        elif isinstance(obj[key], list):
            print(indent_text + f"{key_text}:")
            list_formatter(obj[key], capitalize, indent + 1, list_separator)
        else:
            print(indent_text + f"{key_text}: {obj[key]}")


def list_formatter(
    obj: dict, capitalize: bool = False, indent: int = 0, list_separator: str = None
):
    for item in obj:
        indent_text = get_decoration(indent)
        if isinstance(item, dict):
            dict_formatter(item, capitalize, indent + 1)
        elif isinstance(item, list):
            list_formatter(item, capitalize, indent + 1)
        else:
            print(indent_text + str(item))
        if list_separator:
            print("  " * (indent+1) + list_separator)


def autoformat(
    obj: any,
    capitalize: bool = False,
    indent: int = 0,
    jsonfmt: bool = False,
    list_separator: str = None,
):
    """Format and print a dict, list or other var

    Parameters
    ----------
    obj : any
        Var to print
    capitalize : bool, optional
        Capitalize dict keys, by default False
    ident : bool, optional
        Indent length, by default 0
    jsonfmt: bool, optional
        Print as json, by default False
    list_separator: str, optional
        List separator
    """
    if jsonfmt:
        print(json.dumps(obj, indent=indent, default=str))
    else:
        if isinstance(obj, dict):
            dict_formatter(obj, capitalize, indent, list_separator)
        elif isinstance(obj, list):
            list_formatter(obj, capitalize, indent, list_separator)
        else:
            print(str(obj))


def filter_params(params: any, filter_keys: Union[tuple, list]) -> dict:
    """Filter elements of a dict/namespace according to a list of keys

    Parameters
    ----------
    params : any
        dict or namespace to filter
    filter_keys : Union[tuple, list]
        List of keys to return from dict or namespace

    Returns
    -------
    dict
        Filtered dict
    """
    if not isinstance(params, dict):  # is a namespace?
        params = vars(params)
    filtered = filter(lambda i: i[0] in filter_keys, params.items())
    return dict(filtered)


def check_monitor(playbook):
    with open(playbook) as stream:
        config = yaml.safe_load(stream)
        settings = config.get("settings", {})
        return set() != {"rate", "cron"} & settings.keys()
