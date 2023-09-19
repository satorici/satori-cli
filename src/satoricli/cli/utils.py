import json
import logging
import random
import re
from base64 import b64decode
from dataclasses import dataclass
from itertools import zip_longest
from typing import Any, Optional, Union

import yaml
from rich import print_json
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme

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


# Set rich theme and console
# https://rich.readthedocs.io/en/latest/appendix/colors.html#appendix-colors
class SatoriHighlighter(RegexHighlighter):
    base_style = "satori."
    highlights = [
        r"(?P<value>(?<=:\s)\w+$)",
        r"(?P<email>[\w-]+@([\w-]+\.)+[\w-]+)",
        r"(?P<pass>(?<!\w)((p|P)ass|(c|C)ompleted|(y|Y)es|(t|T)rue)(?!\w))",
        r"(?P<pending>(?<!\w)((p|P)ending|(r|R)unning)(?!\w))",
        r"(?P<fail>(?<!\w)((f|F)ail(\(\d+\))?|(e|E)rror|(n|N)o|(f|F)alse)(?!\w))",
        r"(?P<unknown>(?<!\w)((u|U)nknown|undefined|null|None)(?!\w))",
        r"(?P<satori_com>https?:\/\/(www\.)satori-ci\.com\S+)",
        r"(?P<satori_uri>satori:\/\/\S+)",
        r"(?P<key>([^\w]|^)\w[\w\s]*:\s*)(?!\/\/)",
        r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)",
        r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
        r"(?P<testcase_pass>\w+ > [^:]+: Pass$)",
        r"(?P<testcase_fail>\w+ > [^:]+: Fail$)",
        r"(?P<db_date>\d{4}-\d?\d-\d?\d\w\d{2}:\d{2}:\d{2})",
        r"(?P<id>(r|m|p)\w{15}$)",
    ]


satori_theme = Theme(
    {
        "debug": "dim blue",
        "info": "dim cyan",
        "warning": "yellow",
        "danger": "bold red",
        "error": "red",
        "critical": "on red",
        "multiline": "yellow",
        "satori.email": "cyan",
        "satori.pass": "chartreuse1",
        "satori.pending": "dark_slate_gray3",
        "satori.fail": "bright_red",
        "satori.unknown": "bright_yellow",
        "satori.satori_com": "turquoise2",
        "satori.satori_uri": "dark_turquoise",
        "satori.key": "white b",
        "satori.value": "cyan1",
        "satori.number": "deep_sky_blue1",
        "satori.uuid": "purple",
        "satori.testcase_pass": "green",
        "satori.testcase_fail": "red",
        "satori.db_date": "bright_magenta",
        "satori.id": "blue",
    }
)
console = Console(highlighter=SatoriHighlighter(), theme=satori_theme, log_path=False)
error_console = Console(
    highlighter=SatoriHighlighter(), theme=satori_theme, log_path=False, stderr=True
)

logging.basicConfig(
    level="CRITICAL",
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
)
log = logging.getLogger()


def get_decoration(indent):
    return (
        "[dim]" + "  " * indent + __decorations[indent % len(__decorations)] + " [/dim]"
    )


def dict_formatter(
    obj: dict,
    capitalize: bool = False,
    indent: int = 0,
    list_separator: Union[str, None] = None,
) -> list:
    lines = list()
    for key in obj.keys():
        indent_text = get_decoration(indent)
        key_text = key.capitalize() if capitalize else key
        if isinstance(obj[key], dict):
            lines.append(indent_text + f"{key_text}:")
            lines.append(
                dict_formatter(obj[key], capitalize, indent + 1, list_separator)
            )
        elif isinstance(obj[key], list):
            lines.append(indent_text + f"{key_text}:")
            lines.append(
                list_formatter(obj[key], capitalize, indent + 1, list_separator)
            )
        else:
            item = str(obj[key]).strip()
            lines.append((indent_text + f"{key_text}: ", ""))
            if item.count("\n") > 0:
                lines.append("")  # add empty line
                syntax = autosyntax(item, indent + 2, echo=False)
                if syntax:
                    lines.append(syntax)
                    continue
            # Not JSON or YAML
            lines.append(item)
    return lines


def list_formatter(
    obj: list,
    capitalize: bool = False,
    indent: int = 0,
    list_separator: Optional[str] = None,
) -> list:
    lines = []
    for item in obj:
        indent_text = get_decoration(indent)
        if isinstance(item, dict):
            lines.append(dict_formatter(item, capitalize, indent + 1))
        elif isinstance(item, list):
            lines.append(list_formatter(item, capitalize, indent + 1))
        else:
            item = str(item).strip()
            lines.append(indent_text + item)
        if list_separator:
            lines.append("  " * (indent + 1) + list_separator)
    return lines


def autoformat(
    obj: Any,
    capitalize: bool = False,
    indent: int = 0,
    jsonfmt: bool = False,
    list_separator: Optional[str] = None,
    color: str = "",
    table: bool = False,
    echo: bool = True,
) -> Union[None, str]:
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
    lines = []
    if jsonfmt:
        print_json(json.dumps(obj, default=str), indent=(indent + 1) * 2)
    else:
        if isinstance(obj, dict):
            lines = dict_formatter(obj, capitalize, indent, list_separator)
        elif isinstance(obj, list):
            if table and len(obj) > 0 and isinstance(obj[0], dict) and echo:
                # is a list of dict
                head_color = random.choice(__random_colors)  # nosec
                autotable(obj, f"bold {head_color}")
                return None
            lines = list_formatter(obj, capitalize, indent, list_separator)
        elif isinstance(obj, str):
            if obj.count("\n") > 0:  # multiline
                lines = [autosyntax(obj, indent, echo=False)]
            else:  # singleline
                lines = [obj]
        else:
            lines = [str(obj)]
    lines = flatten_list(lines)
    if echo:
        for line in lines:
            if isinstance(line, tuple):
                console.print(line[0], end=line[1])
            else:
                console.print(line)
    else:
        text = ""
        for line in lines:
            if isinstance(line, tuple):
                text += line[0] + line[1]
            elif isinstance(line, Syntax):
                text += str(line.__doc__) + "\n"
            else:
                text += str(line) + "\n"
        return text


def flatten_list(items: list) -> list:
    out = []
    for item in items:
        if isinstance(item, list):
            out.extend(flatten_list(item))
        else:
            out.append(item)
    return out


def check_monitor(playbook):
    with open(playbook) as stream:
        config = yaml.safe_load(stream)
        settings = config.get("settings", {})
        return set() != {"rate", "cron"} & settings.keys()


def autosyntax(
    item: str,
    indent: int = 0,
    lexer: Optional[str] = None,
    echo: bool = True,
) -> Union[bool, Syntax]:
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
    yml = Syntax(item, final_lexer, padding=(0, ind), theme="ansi_dark", word_wrap=True)
    if echo:
        console.print(yml)
        return True
    else:
        return yml


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
    table = Table(
        show_header=True,
        header_style=header_style,
        row_styles=["on #222222", "on black"],
        expand=True,
    )
    for header, width in zip_longest(headers, widths):
        table.add_column(header, width=width)
    for item in items:
        cells = []
        for raw_i in item:
            if raw_i is None:
                i = "-"
            else:
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
    console.print(table)


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
    if len(items) == 0:
        console.print("No items found")
        return
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


def format_outputs(outputs):
    current_path = ""

    for line in outputs:
        output = json.loads(line)

        if current_path != output["path"]:
            console.rule(f"[b]{output['path']}[/b]")
            current_path = output["path"]

        console.print(f"[b][green]Command:[/green] {output['original']}[/b]")

        if output["testcase"]:
            testcase = Table(show_header=False, show_edge=False)

            testcase.add_column(style="b")
            testcase.add_column()

            for key, value in output["testcase"].items():
                testcase.add_row(key, b64decode(value).decode(errors="ignore"))

            console.print("[blue]Testcase:[/blue]")
            console.print(testcase)

        console.print("[blue]Return code:[/blue]", output["output"]["return_code"])
        console.print("[blue]Stdout:[/blue]")
        if output["output"]["stdout"]:
            console.out(
                b64decode(output["output"]["stdout"]).decode(errors="ignore").strip()
            )
        console.print("[blue]Stderr:[/blue]")
        if output["output"]["stderr"]:
            console.out(
                b64decode(output["output"]["stderr"]).decode(errors="ignore").strip()
            )


@dataclass
class BootstrapTable:
    """Based on https://bootstrap-table.com/docs/api/table-options/#url"""

    total: int
    totalNotFiltered: int
    rows: list[dict]


def group_table(table: BootstrapTable, key: str, default_group: str):
    """Generate multiple tables grouped by a key

    Parameters
    ----------
    table : BootstrapTable
        The original table
    key : str
        The key name that is used to separate the tables
    default_group: str
        The group name by default if is empty
    """
    groups = {}
    for row in table.rows:
        key_value: str = row[key]
        if not key_value:
            # If is empty add to default group
            key_value = default_group
        row.pop(key, None)  # dont print the key again
        if key_value not in groups:
            # Create a new group if doesnt exist
            groups[key_value] = []
        # Add the item to the group
        groups[key_value].append(row)

    # Print the tables
    for group in groups.keys():
        console.rule(f"[b]{group}", style="cyan")
        autotable(groups[group], "bold blue")
