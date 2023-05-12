from typing import Union
import json
import yaml
import re
from typing import Any
from colorama import Fore, Style
from rich.logging import RichHandler
import logging
from rich import print_json
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
import random

__decorations = "▢•○░"
__random_colors = ["green", "blue", "red"]
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
KEYNAME_REGEX = re.compile(r"(([^\w]|^)\w[\w\s]*:\s*)(?!\/\/)")  # ex: "key: "
# Colors outputs
PASS_COLOR = Fore.LIGHTGREEN_EX
FAIL_COLOR = Fore.LIGHTRED_EX
UNKNOWN_COLOR = Fore.LIGHTYELLOW_EX
RUNNING_COLOR = Fore.LIGHTBLUE_EX
KEYNAME_COLOR = Fore.WHITE
SATORIURL_COLOR = Fore.LIGHTBLUE_EX
VALUE_COLOR = Fore.CYAN
MULTILINE_COLOR = Fore.YELLOW

logging.basicConfig(
    level="CRITICAL",
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
)
log = logging.getLogger()
console = Console(log_path=False, log_time=False)


def get_decoration(indent):
    return (
        Style.DIM
        + "  " * indent
        + __decorations[indent % len(__decorations)]
        + " "
        + Style.RESET_ALL
    )


def dict_formatter(
    obj: dict,
    capitalize: bool = False,
    indent: int = 0,
    list_separator: Union[str, None] = None,
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
            color = get_value_color(item)
            print(indent_text + KEYNAME_COLOR + f"{key_text}: ", end="")
            if item.count("\n") > 0:
                if autosyntax(item, indent + 2):
                    continue
            # Not JSON or YAML
            print(color + item + Style.RESET_ALL)


def list_formatter(
    obj: list,
    capitalize: bool = False,
    indent: int = 0,
    list_separator: Union[str, None] = None,
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
    obj: Any,
    capitalize: bool = False,
    indent: int = 0,
    jsonfmt: bool = False,
    list_separator: Union[str, None] = None,
    color: str = "",
    table: bool = False,
) -> None:
    """Format and print a dict, list or other var

    Parameters
    ----------
    obj : Any
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
        print_json(json.dumps(obj, default=str), indent=(indent + 1) * 2)
    else:
        if isinstance(obj, dict):
            dict_formatter(obj, capitalize, indent, list_separator)
        elif isinstance(obj, list):
            if table and len(obj) > 0 and isinstance(obj[0], dict):
                head_color = random.choice(__random_colors)  # nosec
                autotable(obj, f"bold {head_color}")
                return None
            list_formatter(obj, capitalize, indent, list_separator)
        elif isinstance(obj, str):
            if obj.count("\n") > 0:
                if not autosyntax(obj, indent):
                    print(obj)
        else:
            print(color + str(obj) + Style.RESET_ALL)


def filter_params(params: Any, filter_keys: Union[tuple, list]) -> dict:
    """Filter elements of a dict/namespace according to a list of keys

    Parameters
    ----------
    params : Any
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
    color : Any, optional
        Color of the text, by default Style.NORMAL
    """
    # color, args adds an empty space??
    print(color + "".join(args), Style.RESET_ALL, **kargs)


def get_value_color(item: Any) -> str:
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


def autosyntax(item: str, indent: int) -> bool:
    ind = (indent) * 2
    try:
        json.loads(item)
    except Exception:
        try:
            yaml.safe_load(item)
        except Exception:  # Not YAML/JSON
            return False
        else:  # Is YAML
            yml = Syntax(item, "YAML", padding=(0, ind), theme="fruity", word_wrap=True)
            print()
            console.log(yml)
            return True
    else:  # Is JSON
        print()
        print_json(item, indent=ind)
        return True


def table_generator(headers: list, items: list, header_style=None):
    table = Table(show_header=True, header_style=header_style)
    for header in headers:
        table.add_column(header)
    for item in items:
        cells = []
        for i in item:
            if PASS_REGEX.search(i):
                styled = "[green]" + i
            elif FAIL_REGEX.search(i):
                styled = "[red]" + i
            elif UNKNOWN_REGEX.search(i):
                styled = "[yellow]" + i
            elif RUNNING_REGEX.search(i):
                styled = "[blue]" + i
            else:
                styled = i
            cells.append(styled)
        table.add_row(*cells)
    console.log(table)


class argument:
    def __init__(self) -> None:
        self.id = str()
        self.action = str()
        self.profile = str()
        self.debug = bool()
        self.json = bool()
        self.path = str()
        self.data = Any
        self.sync = bool()
        self.timeout = int()
        self.playbook = str()
        self.page = int()
        self.public = bool()


def autotable(items: list[dict], header_style=None) -> None:
    headers = []
    # get headers
    for i in items:
        for h in i.keys():
            if h not in headers:
                headers.append(h)
    rows = []
    # get rows
    for item in items:
        row = []
        for key in headers:
            if key in item:
                row.append(item[key])
            else:
                row.append("")
        rows.append(row)
    table_generator(headers, rows, header_style)
