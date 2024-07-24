import json
import logging
import random
import time
import warnings
from base64 import b64decode
from dataclasses import dataclass
from itertools import zip_longest
from math import ceil
from pathlib import Path
from typing import Any, Optional, Union

import httpx
import yaml
from rich import print_json
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme
from satorici.validator import validate_playbook
from satorici.validator.exceptions import (
    NoExecutionsError,
    PlaybookValidationError,
    PlaybookVariableError,
)
from satorici.validator.warnings import MissingAssertionsWarning

from satoricli.api import client, disable_error_raise
from satoricli.bundler import get_local_files
from satoricli.validations import get_parameters, has_executions

__decorations = "▢•○░"
__random_colors = ["green", "blue", "red"]


@dataclass
class BootstrapTable:
    """Based on https://bootstrap-table.com/docs/api/table-options/#url"""

    total: int
    totalNotFiltered: int
    rows: list[dict]


# Set rich theme and console
# https://rich.readthedocs.io/en/latest/appendix/colors.html#appendix-colors
class SatoriHighlighter(RegexHighlighter):
    base_style = "satori."
    highlights = [
        r"(?P<value>(?<=:\s)\w+$)",
        r"(?P<email>[\w-]+@([\w-]+\.)+[\w-]+)",
        r"(?P<pass>((^|(:|>) )(p|P)ass|(c|C)ompleted|(y|Y)es|(t|T)rue)($|\s))",
        r"(?P<pending>((^|: )(p|P)ending|(r|R)unning)($|\s))",
        r"(?P<fail>((^|(:|>) )(f|F)ail(\(\d+\))?|(e|E)rror|(n|N)o|(f|F)alse)($|\s))",
        r"(?P<unknown>((^|: )(u|U)nknown|undefined|null|None|(S|s)topped)($|\s))",
        r"(?P<satori_com>https?:\/\/(www\.)satori-ci\.com\S+)",
        r"(?P<satori_uri>satori:\/\/\S+)",
        r"(?P<key>([^\w]|^)\w[\w\s]*:\s*)(?!\/\/)",
        r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)",
        r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
        r"(?P<testcase_pass>\w+ > [^:]+: Pass$)",
        r"(?P<testcase_fail>\w+ > [^:]+: Fail$)",
        r"(?P<db_date>\d{4}-\d?\d-\d?\d(\w|\s)\d{2}:\d{2}:\d{2})",
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
        highlight=True,
    )
    for header, width in zip_longest(headers, widths):
        table.add_column(header, width=width)
    for item in items:
        cells = []
        for raw_i in item:
            i = "-" if raw_i is None else str(raw_i)
            cells.append(i)
        table.add_row(*cells)
    console.print(table)


def autotable(
    items: Union[list[dict], BootstrapTable],
    header_style: Optional[str] = None,
    numerate: Optional[bool] = False,
    widths: Union[tuple, list] = [None],
    page: Optional[int] = None,
    limit: Optional[int] = None,
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
    is_bootstrap = isinstance(items, BootstrapTable)
    rows = items.rows if is_bootstrap else items
    if len(rows) == 0:
        console.print("No items found")
        return
    h = get_headers(rows)
    headers = ["N°", *h] if numerate else h
    rows = get_rows(rows, headers)
    table_generator(capitalize_list(headers), rows, header_style, widths)

    if is_bootstrap and page and limit:
        console.print(
            f"Page {page} of {ceil(items.total / limit)} | Total: {items.total}"
        )


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
                b64decode(output["output"]["stdout"]).decode(errors="ignore"),
                highlight=False,
            )
        console.print("[blue]Stderr:[/blue]")
        if output["output"]["stderr"]:
            console.out(
                b64decode(output["output"]["stderr"]).decode(errors="ignore"),
                highlight=False,
            )
        if output["output"]["os_error"]:
            console.out(output["output"]["os_error"])


def group_table(
    table: BootstrapTable,
    key: str,
    default_group: str,
    page: int,
    limit: int,
    widths: Union[tuple, list] = [None],
):
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
        autotable(groups[group], "bold blue", widths=widths)

    console.print(f"Page {page} of {ceil(table.total / limit)} | Total: {table.total }")


def wait(report_id: str):
    with Progress(
        SpinnerColumn("dots2"),
        TextColumn("[progress.description]Status: {task.description}"),
        TimeElapsedColumn(),
        console=error_console,
    ) as progress:
        task = progress.add_task("Fetching data")
        status = "Unknown"

        while status not in ("Completed", "Stopped"):
            with disable_error_raise() as c:
                res = c.get(f"/reports/{report_id}/status")

            if res.is_success:
                status = res.text
            elif res.is_client_error:
                status = "Unknown"
            else:
                return

            progress.update(task, description=status)
            time.sleep(1)


def download_files(report_id: str):
    r = client.get(f"/outputs/{report_id}/files")
    with httpx.stream("GET", r.json()["url"]) as s:
        total = int(s.headers["Content-Length"])

        with Progress(console=error_console) as progress:
            task = progress.add_task("Downloading...", total=total)

            with open(f"satorici-files-{report_id}.tar.gz", "wb") as f:
                for chunk in s.iter_raw():
                    progress.update(task, advance=len(chunk))
                    f.write(chunk)


def print_output(report_id: str, print_json: bool = False):
    r = client.get(f"/outputs/{report_id}")
    with httpx.stream("GET", r.json()["url"], timeout=300) as s:
        if print_json:
            for line in s.iter_lines():
                console.out(line, highlight=False)
        else:
            format_outputs(s.iter_lines())


def print_summary(report_id: str, print_json: bool = False):
    report_data = client.get(f"/reports/{report_id}").json()

    if comments := report_data.get("user_warnings"):
        error_console.print(f"[error]Error:[/] {comments}")

    result = report_data.get("result", "Unknown")

    if "fails" in report_data and result != "Unknown":
        fails = report_data["fails"]
        result = "Pass" if not fails else f"Fail({fails})"
    else:
        fails = 1

    if print_json:
        console.print_json(data={"report_id": report_id, "result": result})
    else:
        console.print("Result:", result)

    return 0 if fails == 0 else 1


def add_table_row(row_content: list, table: Table, echo: bool = True):
    available_size = console.width - 4
    row_text = ""
    n = 0
    for content in row_content:
        n += 1
        value = f"[{content[2]}]{content[1]}[/]" if len(content) == 3 else content[1]
        text = f"[b]{content[0]}:[/] {value}"
        if n < len(row_content):  # avoid to add separators to the last column
            text += " | "
        if len(text) - 6 > available_size:
            text = "\n" + text
            available_size = console.width - 4
        available_size -= len(content[0]) + len(str(content[1])) + 2  # 2: ": "
        row_text += text
    if echo:
        table.add_row(row_text)
    else:
        return row_text


def validate_config(playbook: Path, params: set):
    try:
        config = yaml.safe_load(playbook.read_text())
    except yaml.YAMLError as e:
        error_console.print(
            f"Error parsing the playbook [bold]{playbook.name}[/]:\n", e
        )
        return False

    try:
        with warnings.catch_warnings(record=True) as w:
            validate_playbook(config)

        for warning in w:
            if warning.category == MissingAssertionsWarning:
                error_console.print("[warning]WARNING:[/] No asserts were defined")
    except TypeError:
        error_console.print("Error: playbook must be a mapping type")
        return False
    except (PlaybookVariableError, NoExecutionsError):
        pass
    except PlaybookValidationError as e:
        error_console.print(
            f"Validation error on playbook [bold]{playbook.name}[/]:\n", e
        )
        return False

    if not has_executions(config, playbook.parent):
        error_console.print("[error]No executions found")
        return False

    variables = get_parameters(config)

    if variables - params:
        error_console.print(f"[error]Required parameters: {variables - params}")
        return False

    return True


def missing_ymls(playbook: dict, root: str):
    local_ymls = list(filter(lambda p: p.is_file(), Path(root).rglob(".satori.yml")))
    imported = get_local_files(playbook)["imports"]

    if len(local_ymls) > 1 and len(local_ymls) - 1 > len(imported):
        return True

    return False


def get_offset(page, limit):
    return (page - 1) * limit


def detect_boolean(s: Any) -> Optional[bool]:
    if not isinstance(s, str):
        return None
    s = s.lower()
    if s in ("true", "on", "y", "yes", "1"):
        return True
    elif s in ("false", "off", "n", "no", "0"):
        return False
    else:
        return None
