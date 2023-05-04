from typing import Union
import json
import yaml
import re
from colorama import Fore, Style

__decorations = "▢•○░"
# IDs
UUID4_REGEX = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.I,
)
# Regex
PASS_REGEX = re.compile(r"(pass|completed)", re.IGNORECASE)
RUNNING_REGEX = re.compile(r"(pending|running)", re.IGNORECASE)
FAIL_REGEX = re.compile(r"(fail(\(\d+\))?|error)", re.IGNORECASE)
UNKNOWN_REGEX = re.compile(r"(unknown|undefined)", re.IGNORECASE)
SATORIURL_REGEX = re.compile(r"(https?:\/\/(www\.)satori-ci\.com\S+)")
KEYNAME_REGEX = re.compile(r"(([^\w]|^)\w[\w\s]*:\s*)(?!\/\/)")
# Colors outputs
PASS_COLOR = Fore.LIGHTGREEN_EX
FAIL_COLOR = Fore.LIGHTRED_EX
UNKNOWN_COLOR = Fore.LIGHTYELLOW_EX
RUNNING_COLOR = Fore.LIGHTBLUE_EX
KEYNAME_COLOR = Fore.WHITE
SATORIURL_COLOR = Fore.LIGHTBLUE_EX
VALUE_COLOR = Fore.CYAN
MULTILINE_COLOR = Fore.YELLOW


def get_decoration(indent):
    return (
        Style.DIM
        + "  " * indent
        + __decorations[indent % len(__decorations)]
        + " "
        + Style.RESET_ALL
    )


def dict_formatter(
    obj: dict, capitalize: bool = False, indent: int = 0, list_separator: str = None
):
    for key in obj.keys():
        indent_text = get_decoration(indent)
        key_text = key.capitalize() if capitalize else key
        if isinstance(obj[key], dict):
            print(indent_text + KEYNAME_COLOR + f"{key_text}:" + Style.RESET_ALL)
            dict_formatter(obj[key], capitalize, indent + 1, list_separator)
        elif isinstance(obj[key], list):
            print(indent_text + KEYNAME_COLOR + f"{key_text}:" + Style.RESET_ALL)
            list_formatter(obj[key], capitalize, indent + 1, list_separator)
        else:
            item = str(obj[key])
            print(
                indent_text
                + KEYNAME_COLOR
                + f"{key_text}: "
                + get_value_color(item)
                + item
                + Style.RESET_ALL
            )


def list_formatter(
    obj: dict, capitalize: bool = False, indent: int = 0, list_separator: str = None
):
    for item in obj:
        indent_text = get_decoration(indent)
        if isinstance(item, dict):
            dict_formatter(item, capitalize, indent + 1, list_separator)
        elif isinstance(item, list):
            list_formatter(item, capitalize, indent + 1, list_separator)
        else:
            item = str(item)
            print(indent_text + get_value_color(item) + item + Style.RESET_ALL)
        if list_separator:
            print(
                "  " * (indent + 1)
                + Fore.LIGHTBLACK_EX
                + list_separator
                + Style.RESET_ALL
            )


def autoformat(
    obj: any,
    capitalize: bool = False,
    indent: int = 0,
    jsonfmt: bool = False,
    list_separator: str = None,
    color: any = "",
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
            print(color + str(obj) + Style.RESET_ALL)


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


def puts(color: str = Style.NORMAL, *args, **kargs):
    """Print with colors, resets the color after printing

    Parameters
    ----------
    color : any, optional
        Color of the text, by default Style.NORMAL
    """
    # color, args adds an empty space??
    print(color + "".join(args), Style.RESET_ALL, **kargs)


def get_value_color(item: any) -> str:
    item = str(item)
    color = VALUE_COLOR
    if item.count("\n") > 0:
        color = f"\n{MULTILINE_COLOR}"
    else:
        if PASS_REGEX.search(item):
            color = PASS_COLOR
        elif FAIL_REGEX.search(item):
            color = FAIL_COLOR
        elif UNKNOWN_REGEX.search(item):
            color = UNKNOWN_COLOR
        elif RUNNING_REGEX.search(item):
            color = RUNNING_COLOR
        elif SATORIURL_REGEX.search(item):
            color = SATORIURL_COLOR
    return color


def autocolor(txt: str) -> str:
    rst = Style.RESET_ALL
    if txt.count("\n") > 0:
        txt = KEYNAME_REGEX.sub(rf"{KEYNAME_COLOR}\1\n{MULTILINE_COLOR}", txt + rst, 1)
        return txt
    txt = KEYNAME_REGEX.sub(rf"{KEYNAME_COLOR}\1{VALUE_COLOR}", txt)
    txt = PASS_REGEX.sub(rf"{PASS_COLOR}\1{rst}", txt)
    txt = RUNNING_REGEX.sub(rf"{RUNNING_COLOR}\1{rst}", txt)
    txt = FAIL_REGEX.sub(rf"{FAIL_COLOR}\1{rst}", txt)
    txt = UNKNOWN_REGEX.sub(rf"{UNKNOWN_COLOR}\1{rst}", txt)
    txt = SATORIURL_REGEX.sub(rf"{SATORIURL_COLOR}\1{rst}", txt)
    return txt
