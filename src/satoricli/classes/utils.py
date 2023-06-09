from typing import Union, Optional
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
from rich.theme import Theme
import random

__decorations = "▢•○░"
__random_colors = ["green", "blue", "red"]
# IDs
UUID4_REGEX = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.I,
)
# Regex
PASS_REGEX = re.compile(r"(pass|completed|^yes$)", re.IGNORECASE)
RUNNING_REGEX = re.compile(r"(pending|running)", re.IGNORECASE)
FAIL_REGEX = re.compile(r"(fail(\(\d+\))?|(?<!\w)error(?!\w)|^no$)", re.IGNORECASE)
UNKNOWN_REGEX = re.compile(r"(unknown|undefined)", re.IGNORECASE)
SATORIURL_REGEX = re.compile(r"(https?:\/\/(www\.)satori-ci\.com\S+)")
KEYNAME_REGEX = re.compile(r"(([^\w]|^)\w[\w\s]*:\s*)(?!\/\/)")  # ex: "key: "

# Colors outputs | TODO: remove this
PASS_COLOR = Fore.LIGHTGREEN_EX
FAIL_COLOR = Fore.LIGHTRED_EX
UNKNOWN_COLOR = Fore.LIGHTYELLOW_EX
RUNNING_COLOR = Fore.LIGHTBLUE_EX
KEYNAME_COLOR = Fore.WHITE
SATORIURL_COLOR = Fore.LIGHTBLUE_EX
VALUE_COLOR = Fore.CYAN
MULTILINE_COLOR = Fore.YELLOW

# Set rich theme and console
# https://rich.readthedocs.io/en/latest/appendix/colors.html#appendix-colors
satori_theme = Theme(
    {
        "debug": "dim blue",
        "info": "dim cyan",
        "warning": "yellow",
        "danger": "bold red",
        "error": "red",
        "critical": "on red",
        "pass": "bright_blue",
        "fail": "bright_red",
        "unknown": "bright_yellow",
        "running": "bright_blue",
        "key": "white",
        "value": "cyan",
        "multiline": "yellow",
    }
)
console = Console(log_path=False, log_time=False, theme=satori_theme)

logging.basicConfig(
    level="CRITICAL",
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
)
log = logging.getLogger()


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
    list_separator: Optional[str] = None,
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
    list_separator: Optional[str] = None,
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
    """[deprecated] Print with colors, resets the color after printing.
    Use console.print(str) or console.log(object) instead

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


def autosyntax(item: str, indent: int = 0, lexer: Optional[str] = None) -> bool:
    ind = (indent) * 2
    lang = None
    if lexer is None:
        try:
            json.loads(item)
        except Exception:
            try:
                yaml.safe_load(item)
            except Exception:  # Not YAML/JSON
                return False
            else:  # Is YAML
                lang = "YAML"
        else:  # Is JSON
            lang = "JSON"
    final_lexer = lexer or lang
    if final_lexer is None:
        return False
    yml = Syntax(item, final_lexer, padding=(0, ind), theme="fruity", word_wrap=True)
    console.log(yml)
    return True


def table_generator(
    headers: list[str],
    items: list[list],
    header_style: Optional[str] = None,
    widths: Union[tuple, list] = [None],
):
    """Print a rich table

    Parameters
    ----------
    headers : list
        A list of the headers names, ex: ["header1","header2"]
    items : list
        A list of rows with cells, ex: [["row1-1","row1-2"],["row2-1","row2-2"]]
    header_style : str, optional
        Rich Table header style, by default None
    """
    widths_iter = iter_loop(widths)
    table = Table(
        show_header=True,
        header_style=header_style,
        row_styles=["on #222222", "on black"],
        expand=True,
    )
    for header in headers:
        table.add_column(header, width=next(widths_iter))
    for item in items:
        cells = []
        for raw_i in item:
            i = str(raw_i)
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


def autotable(
    items: list[dict],
    header_style: Optional[str] = None,
    numerate: Optional[bool] = False,
    widths: Union[tuple, list] = [None],
) -> None:
    """Print a list of dictionaries like a table

    Parameters
    ----------
    items : list[dict]
        The list, ex: [{"id":1,"name":"one"},{"id":2,"name":"two"}]
    header_style : str, optional
        Rich Table header style, by default None
    numerate : bool, optional
        Add numeration, by default False
    """
    h = get_headers(items)
    headers = ["N°", *h] if numerate else h
    rows = get_rows(items, headers)
    table_generator(capitalize_list(headers), rows, header_style, widths)


def get_headers(items: list[dict]) -> list[str]:
    headers = []
    for i in items:
        for h in i.keys():
            h = str(h)
            if h not in headers:
                headers.append(h)
    return headers


def get_rows(items: list[dict], headers: list[str]) -> list[list]:
    rows = []
    n = 0
    for item in items:
        n += 1
        row = []
        for key in headers:
            if key == "N°":  # add numeration
                row.append(str(n))
            elif key in item:
                row.append(item[key])
            else:
                row.append("")
        rows.append(row)
    return rows


def capitalize_list(items: list[str]) -> list[str]:
    new_list = map(lambda x: x.capitalize() if len(x) > 2 else x.upper(), items)
    return list(new_list)


def iter_loop(data: Union[tuple[Any], list[Any]]):
    i = 0
    while True:
        yield data[i]
        i += 1
        if i >= len(data):
            i = 0
