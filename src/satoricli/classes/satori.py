import ast
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
import warnings
from argparse import Namespace
from base64 import b64decode
from pathlib import Path

import requests
import yaml
from colorama import Fore
from rich.progress import open as progress_open, Progress
from rich.table import Table
from satorici.validator import validate_playbook
from satorici.validator.exceptions import PlaybookValidationError, PlaybookVariableError
from satorici.validator.warnings import NoLogMonitorWarning

from .api import SatoriAPI
from .bundler import get_local_files, make_bundle
from .models import arguments
from .playbooks import display_public_playbooks
from .utils import (
    FAIL_COLOR,
    KEYNAME_COLOR,
    SATORIURL_COLOR,
    UUID4_REGEX,
    VALUE_COLOR,
    autocolor,
    autoformat,
    autotable,
    check_monitor,
    console,
    filter_params,
    log,
    puts,
)
from .validations import get_parameters, validate_parameters


class Satori:
    """Have some class"""

    def __init__(self, args: arguments, config=False) -> None:
        """Turn on the engines"""
        self.profile = args.profile
        self.config_paths = [
            f"{Path.home()}/.satori_credentials.yml",
            ".satori_credentials.yml",
        ]
        self.verbose = False
        if not config:
            self.load_config()
            self.api = SatoriAPI(self.token, self.server, args)

    def load_config(self) -> None:
        """Load the config file and set the token on the headers"""
        config_file = None
        for file in self.config_paths:
            if Path(file).is_file():
                config_file = Path(file)
                break

        if not config_file:
            print("No config file")
            print("")
            print("Configure your credentials")
            print("satori-cli [-p PROFILE] config token TOKEN")
            sys.exit(1)

        with config_file.open(encoding="utf-8") as f:
            config: dict[str, dict[str, str]] = yaml.safe_load(f)
            if not isinstance(config, dict):
                puts(FAIL_COLOR, "Invalid config format")
                sys.exit(1)

            profile = config.get(self.profile)

            if not (profile and isinstance(profile, dict)):
                puts(FAIL_COLOR, "Invalid or non existent profile")
                profile_list = list(config.keys())
                print(f"Profiles list: {', '.join(profile_list)}")
                sys.exit(1)

            if not profile.get("token"):
                puts(FAIL_COLOR, f"No token in profile: {self.profile}\n")
                print("satori-cli [-p PROFILE] config token TOKEN")
                sys.exit(1)

            self.config = config
            self.token = profile["token"]
            self.server = profile.get("server")

    def save_config(self, key: str, value: str):
        """Save the token into the config file"""
        config_file = None
        for file in self.config_paths:
            if Path(file).is_file():
                config_file = Path(file)
                break

        if config_file:
            with config_file.open() as f:
                config = yaml.safe_load(f)
                if not isinstance(config, dict):
                    puts(FAIL_COLOR, "Invalid config format")
                    sys.exit(1)
        else:
            config = {}
            config_file = self.config_paths[0]

        config.setdefault(self.profile, {})[key] = value
        try:
            with open(config_file, "w") as f:
                os.chmod(config_file, 0o600)
                f.write(yaml.safe_dump(config))
        except Exception:
            puts(
                FAIL_COLOR,
                "Could not write to home directory, writing into current directory",
            )
            config_file = self.config_paths[1]
            with open(config_file, "w") as f:
                os.chmod(config_file, 0o600)
                f.write(yaml.safe_dump(config))
        puts(Fore.LIGHTGREEN_EX, key.capitalize() + " saved")

    def run(self, args: arguments):
        if args.path.startswith("satori://"):
            self.run_url(args)

        path = Path(args.path)
        params = set()

        if getattr(args, "data", False):
            try:
                data = ast.literal_eval(args.data)

                if not validate_parameters(data):
                    raise ValueError("Malformed parameters")

                params.update(data.keys())
            except Exception as e:
                puts(FAIL_COLOR, str(e))
                sys.exit(1)

        if path.is_dir():
            playbook = path / ".satori.yml"
        elif path.is_file():
            playbook = path
        else:
            puts(FAIL_COLOR, "Playbook file or folder not found")
            sys.exit(1)

        playbook_text = playbook.read_text()
        config = None

        try:
            config = yaml.safe_load(playbook_text)

            with warnings.catch_warnings(record=True) as w:
                validate_playbook(config)

            for warning in w:
                if warning.category == NoLogMonitorWarning:
                    console.print(
                        "[warning]WARNING:[/] No notifications (log, onLogFail or onLogPass) were defined for the Monitor"
                    )
        except yaml.YAMLError as e:
            console.print(f"Error parsing the playbook [bold]{playbook.name}[/]:\n", e)
            sys.exit(1)
        except PlaybookVariableError:
            pass
        except PlaybookValidationError as e:
            console.print(
                f"Validation error on playbook [bold]{playbook.name}[/]:\n", e
            )
            sys.exit(1)

        if not isinstance(config, dict):
            console.print("[error]Failed to load the playbook")
            sys.exit(1)

        variables = get_parameters(config)

        if variables - params:
            console.print(f"[error]Required parameters: {variables - params}")
            sys.exit(1)

        if path.is_dir():
            exec_data = self.run_folder(args)
        else:  # is file
            exec_data = self.run_file(args)
        if (args.sync or args.output or args.report or args.files) and exec_data:
            self.run_sync(exec_data, args)

    def run_file(self, args: arguments) -> dict:
        """Just run"""
        playbook = args.path
        bundle = make_bundle(playbook)
        is_monitor = check_monitor(playbook)
        url = self.api.runs("bundle", {"secrets": args.data})
        log.debug(url)
        res = requests.post(  # nosec
            url["url"], url["fields"], files={"file": bundle}, timeout=None
        )
        log.debug(res.text)
        if not res.ok:
            puts(FAIL_COLOR, "File upload failed")
            sys.exit(1)
        if is_monitor:
            exec_type = "monitor"
            exec_id = url["monitor"]
            print(KEYNAME_COLOR + "Monitor ID: " + VALUE_COLOR + f"{exec_id}")
            print(autocolor(f"Status: https://www.satori-ci.com/status?id={exec_id}"))
        else:
            exec_type = "report"
            exec_id = url["fields"]["key"].split("/")[1]
            print(KEYNAME_COLOR + "Report ID: " + VALUE_COLOR + f"{exec_id}")
            print(
                KEYNAME_COLOR
                + "Report: "
                + SATORIURL_COLOR
                + f"https://www.satori-ci.com/report_details/?n={exec_id}"
            )
        return {"type": exec_type, "id": exec_id}

    def run_folder(self, args: arguments) -> dict:
        """Upload directory and run"""
        directory = args.path
        satori_yml = Path(directory, ".satori.yml")
        bundle = make_bundle(str(satori_yml), from_dir=True)
        is_monitor = check_monitor(satori_yml)
        temp_file = Path(tempfile.gettempdir(), str(uuid.uuid4()))
        full_path = f"{temp_file}.tar.gz"

        local_ymls = list(
            filter(lambda p: p.is_file(), Path(args.path).rglob(".satori.yml"))
        )

        imported = get_local_files(yaml.safe_load(satori_yml.read_text()))["imports"]

        if len(local_ymls) > 1 and len(local_ymls) - 1 > len(imported):
            console.print("[warning]There are some .satori.yml not imported")

        try:
            shutil.make_archive(str(temp_file), "gztar", directory)
        except Exception as e:
            puts(FAIL_COLOR, f"Could not compress directory: {e}")
            sys.exit(1)

        res = self.api.runs("archive", {"secrets": args.data})
        log.debug(res)
        arc = res["archive"]
        bun = res["bundle"]
        mon = res["monitor"]

        try:
            with progress_open(full_path, "rb", description="Uploading...") as f:
                res = requests.post(  # nosec
                    arc["url"], arc["fields"], files={"file": f}, timeout=None
                )
        finally:
            os.remove(full_path)

        if not res.ok:
            print("Archive upload failed")
            sys.exit(1)

        res = requests.post(  # nosec
            bun["url"], bun["fields"], files={"file": bundle}, timeout=None
        )
        log.debug(res.text)
        if not res.ok:
            print("Bundle upload failed")
            sys.exit(1)

        if is_monitor:
            exec_type = "monitor"
            exec_id = mon
            print(KEYNAME_COLOR + "Monitor ID: " + VALUE_COLOR + f"{mon}")
            print(autocolor(f"Status: https://www.satori-ci.com/status?id={mon}"))
        else:
            exec_type = "report"
            exec_id = bun["fields"]["key"].split("/")[1]
            print(KEYNAME_COLOR + "Report ID: " + VALUE_COLOR + f"{exec_id}")
            print(
                autocolor(
                    f"Report: https://www.satori-ci.com/report_details/?n={exec_id}"
                )
            )
        return {"type": exec_type, "id": exec_id}

    def run_url(self, args: arguments):
        info = self.api.runs("url", {"secrets": args.data, "url": args.path})
        autoformat({"Running with the ID": info.get("report_id")}, jsonfmt=args.json)
        if args.sync or args.output or args.report:
            exec_data = {"type": "report", "id": info["report_id"]}
            self.run_sync(exec_data, args)
        sys.exit(0)

    def run_sync(self, exec_data: dict, args: arguments) -> None:
        if exec_data["type"] == "monitor":
            console.print(
                "[warning]WARNING:[/] Sync mode is not supported for monitors"
            )
            sys.exit(0)
        console.print("[key]Fetching data...", end="\r")
        start_time = time.time()
        spin = "-\\|/"
        pos = 0
        while True:
            pos += 1
            if pos >= len(spin):
                pos = 0
            time.sleep(1)
            elapsed = time.time() - start_time
            elapsed_text = f"Elapsed time: {elapsed:.1f}s"
            try:
                report_data = self.api.reports(
                    "GET", exec_data["id"], "", raise_error=True
                )
            except requests.HTTPError as e:
                code = e.response.status_code
                if code in (404, 403):
                    print(
                        autocolor(
                            f"{spin[pos]} Report status: Unknown | {elapsed_text}"
                        ),
                        end="\r",
                    )
                    continue
                else:
                    console.print(f"[error]Failed to get data\n[/]Status code: {code}")
                    sys.exit(1)

            status = report_data.get("status", "Unknown")
            if status in ("Completed", "Undefined"):
                fails = report_data["fails"]
                if isinstance(fails, int):
                    result = "Pass" if fails == 0 else f"Fail({fails})"
                else:
                    result = "Unknown"
                print(
                    autocolor(
                        f"- Report status: {status} | Result: {result} | {elapsed_text}"
                    ),
                    end="\r\n",
                )
                if args.report:  # --report or -r
                    report_out = []
                    # Remove keys
                    json_data = report_data.get("json") or []
                    for report in json_data:
                        report.pop("gfx", None)
                        report_out.append(report)
                        asserts = []
                        for asrt in report["asserts"]:
                            asrt.pop("count", None)
                            asrt.pop("description", None)
                            if len(asrt.get("data", [])) == 0:
                                asrt.pop("data", None)
                            asserts.append(asrt)
                    autoformat(report_out, list_separator="- " * 20)
                elif args.output:
                    out_args = Namespace(
                        id=exec_data["id"], action="output", json=args.json
                    )
                    self.output(out_args.id)
                elif args.files:
                    self.output_files(exec_data["id"])
                else:  # --sync or -s
                    # TODO: print something else?
                    pass  # already printed
                if status == "Undefined":
                    comments = report_data.get("comments")
                    if comments:
                        puts(FAIL_COLOR, f"Error: {comments}")
                    sys.exit(1)
                else:  # Completed
                    # Return code 0 if report status==pass else 1
                    sys.exit(0 if report_data["fails"] == 0 else 1)
            else:
                print(
                    autocolor(f"{spin[pos]} Report status: {status} | {elapsed_text}"),
                    end="\r",
                )

    def repo(self, args: arguments):
        """Run Satori on multiple commits"""
        params = filter_params(args, ("id",))
        if args.playbook:
            playbook = Path(args.playbook)
            if playbook.is_file():
                args.playbook = playbook.read_text()
        if args.action == "scan":
            params = filter_params(
                args, ("coverage", "from", "to", "branch", "data", "playbook")
            )
            params["url"] = args.id
            info = self.api.repos_scan("GET", "", "", params=params)
        elif args.action == "clean":
            params = filter_params(args, ("id", "delete_commits"))
            info = self.api.repos("GET", args.id, args.action, params=params)
        elif args.action == "tests":
            params = filter_params(args, ("id", "filter", "all", "limit", "fail"))
            info = self.api.repos("GET", args.id, args.action, params=params)
        elif args.action == "run":
            params = filter_params(args, ("data", "playbook"))
            params["url"] = args.id
            info = self.api.repos_scan("GET", "", "last", params=params)
            if args.sync:
                if len(info) == 1:
                    console.print(
                        "Report: [link]https://www.satori-ci.com/report_details/?n="
                        + info[0]["status"].replace("Report running ", "")
                    )
                self.sync_reports_list(info)
        elif args.action == "scan-stop":
            info = self.api.repos_scan("GET", args.id, "stop", params=params)
        elif args.action == "scan-status":
            info = self.api.repos_scan("GET", args.id, "status", params=params)
        elif args.action == "check-forks":
            info = self.api.repos_scan("GET", args.id, args.action, params=params)
        elif args.action == "check-commits":
            params = filter_params(args, ("id", "branch"))
            info = self.api.repos_scan("GET", args.id, args.action, params=params)
        elif args.action in ("commits", "", "download", "pending"):
            info = self.api.repos("GET", args.id, args.action, params=params)
        else:
            puts(FAIL_COLOR, "Unknown subcommand")
            sys.exit(1)

        if args.id != "" or args.action != "" or args.json:
            autoformat(info, jsonfmt=args.json, list_separator="-" * 48)
        else:  # Default command (satori-cli repo)
            if len(info["pending"]) > 1:
                console.rule("[b red]Pending actions", style="red")
                autotable(info["pending"], "bold red", widths=(50, 50))
            console.rule("[b green]GitHub Repositories", style="green")
            autotable(info["list"], "bold blue", widths=(None, 10, 12, 20, 10, 40))
        if args.action == "run" and args.sync:
            if isinstance(info, list):
                info = info[0]
            report = info.get("status", "")
            match = UUID4_REGEX.findall(report)
            if match:
                self.run_sync({"type": "report", "id": match[0]}, args)

    def report(self, args: arguments):
        """Show a list of reports"""
        params = filter_params(args, ("id",))
        if args.action == "":  # default: print reports
            params = filter_params(args, ("id", "page", "limit", "filter"))
            res = self.api.reports("GET", args.id, "", params=params)
            if args.id == "" and not args.json:  # default: print list
                autoformat(res["list"])
                console.print(
                    f"[b]Page:[/] {res['current_page']} of {res['total_pages']}"
                )
            else:  # single report or json output
                autoformat(res, jsonfmt=args.json)
        elif args.action == "output":
            self.output(args.id)
        elif args.action == "files":
            self.output_files(args.id)
        elif args.action == "stop":
            res = self.api.reports("GET", args.id, "stop")
            autoformat(res, jsonfmt=args.json)
        elif args.action == "delete":
            self.api.report_delete(params)
            print("Report deleted")
        else:
            print("Unknown subcommand")
            sys.exit(1)

    def monitor(self, args: arguments):
        """Get information about the"""
        params = filter_params(args, ("id",))
        if args.action == "delete":
            params = filter_params(args, ("clean",))
            self.api.request("DELETE", f"monitors/{args.id}", params=params)
            print("Monitor deleted")
            sys.exit(0)
        elif args.action == "":
            params = filter_params(args, ("id", "deleted"))
            info = self.api.monitors("GET", args.id, "", params=params)
        elif args.action in ("start", "stop"):
            info = self.api.monitors("PATCH", args.id, args.action)
        else:
            print("Unknown subcommand")
            sys.exit(1)
        if args.id != "" or args.action != "" or args.json:
            autoformat(info, jsonfmt=args.json, list_separator="*" * 48)
        else:  # Default command (satori-cli monitor)
            if len(info["pending"]) > 1:
                console.rule("[b red]Pending actions", style="red")
                autotable(info["pending"], "b red")
            console.rule("[b blue]Monitors", style="blue")
            autotable(info["list"], "b blue")

    def output(self, report_id: str):
        """Returns commands output"""
        current_path = ""

        for line in self.api.get_report_output(report_id):
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
                    b64decode(output["output"]["stdout"])
                    .decode(errors="ignore")
                    .strip()
                )
            console.print("[blue]Stderr:[/blue]")
            if output["output"]["stderr"]:
                console.out(
                    b64decode(output["output"]["stderr"])
                    .decode(errors="ignore")
                    .strip()
                )

    def output_files(self, report_id: str):
        r = self.api.get_report_files(report_id)
        total = int(r.headers["Content-Length"])

        with Progress() as progress:
            task = progress.add_task("Downloading...", total=total)

            with open(f"satorici-files-{report_id}.tar.gz", "wb") as f:
                for chunk in r.iter_content():
                    progress.update(task, advance=len(chunk))
                    f.write(chunk)

    def dashboard(self, args: arguments):
        """Get user dashboard"""
        info = self.api.dashboard()
        if args.json:
            autoformat(info, jsonfmt=True)
        else:
            len_mon = len(info["monitors"]["pending"])
            len_rep = len(info["repos"]["pending"])
            if len_mon > 0 or len_rep > 0:
                # print pending actions
                if len_mon > 0:
                    console.rule(
                        "[b][blue]Monitors[/blue] (Actions required)", style="white"
                    )
                    autotable(
                        info["monitors"]["pending"], "b blue", widths=(20, 20, None)
                    )
                if len_rep > 0:
                    console.rule(
                        "[b][green]GitHub Repositories[/green] (Actions required)",
                        style="white",
                    )
                    autotable(info["repos"]["pending"], "b green", widths=(50, 50))
            if len(info["monitors"]["list"]) == 0:
                console.print("[b]Monitors:[red] no active monitors defined")
            else:
                console.rule("[b blue]Monitors", style="blue")
                autotable(info["monitors"]["list"], "b blue", True)
            if len(info["repos"]["list"]) > 0:
                console.rule("[b green]Github Repositories", style="green")
                autotable(
                    info["repos"]["list"],
                    "b green",
                    True,
                    widths=(3, None, 10, 12, 20, 10, 40),
                )

    def playbook(self, args: arguments):
        """Get playbooks"""
        if args.public or args.id.startswith("satori://"):
            display_public_playbooks(args.id)

        if args.action == "":
            if args.id == "":
                # Default: get list of user playbooks
                params = filter_params(args, ("limit", "page"))
                data = self.api.playbook("GET", "", params)
            else:
                data = self.api.playbook("GET", args.id)
        elif args.action == "delete":
            data = self.api.playbook("DELETE", args.id)
            print("Playbook Deleted")
            sys.exit(0)
        else:
            print("Unknown subcommand")
            sys.exit(1)
        autoformat(data, jsonfmt=args.json, list_separator="-" * 48)

    def team(self, args: arguments):
        """Get information about the"""
        params = filter_params(args, ("id",))
        if args.action == "":
            info = self.api.teams("GET", args.id, "", params=params)
        elif args.action == "create":
            info = self.api.teams("POST", args.id, "", json=params)
        elif args.action == "members":
            info = self.api.teams("GET", args.id, "members", params=params)
        elif args.action == "add_member":
            params = filter_params(args, ("id", "email", "role"))
            info = self.api.teams("POST", args.id, "members", json=params)
        elif args.action == "repos":
            info = self.api.teams("GET", args.id, "repos", data=params)
        elif args.action == "add_repo":
            params = filter_params(args, ("id", "repo"))
            info = self.api.teams("POST", args.id, "repos", json=params)
        elif args.action == "get_config":
            info = self.api.teams("GET", args.id, f"config/{args.config_name}")
        elif args.action == "set_config":
            info = self.api.teams(
                "PUT",
                args.id,
                "config",
                json={"name": args.config_name, "value": args.config_value},
            )
        elif args.action == "get_token":
            info = self.api.teams("GET", args.id, "token")
        elif args.action == "refresh_token":
            info = self.api.teams("PUT", args.id, "token")
        elif args.action == "delete":
            self.api.request("DELETE", f"teams/{args.id}")
            console.print("Team deleted")
            sys.exit(0)
        elif args.action == "del_member":
            self.api.request(
                "DELETE", f"teams/{args.id}/members", json={"email": args.email}
            )
            console.print("Team member deleted")
            sys.exit(0)
        else:
            print("Unknown subcommand")
            sys.exit(1)
        autoformat(info, jsonfmt=args.json, list_separator="*" * 48, table=True)

    def sync_reports_list(self, report_list: list[dict]) -> None:
        completed = []
        n = 0
        with console.status("[bold cyan]Getting results...") as report:
            while len(completed) < len(report_list):
                report = report_list[n]["status"].replace("Report running ", "")
                repo = report_list[n]["repo"]
                if repo not in completed:
                    if report == "Failed to scan commit":
                        console.print(f"[bold]{repo}[/bold] [red]Failed to start")
                        completed.append(repo)
                    try:
                        report_data = self.api.reports(
                            "GET", report, "", raise_error=True
                        )
                    except requests.HTTPError as e:
                        code = e.response.status_code
                        if code not in (404, 403):
                            console.print(
                                f"[red]Failed to get data\nStatus code: {code}"
                            )
                            sys.exit(1)
                    else:
                        report_status = report_data.get("status", "Unknown")
                        if report_status in ("Completed", "Undefined"):
                            fails = report_data["fails"]
                            if fails is None:
                                result = "[yellow]Unknown"
                            else:
                                result = (
                                    "[green]Pass"
                                    if fails == 0
                                    else f"[red]Fail({fails})"
                                )
                            console.print(
                                f"[bold]{repo}[/bold] Completed | Result: {result}"
                            )
                            completed.append(repo)
                time.sleep(0.5)
                n += 1
                if n >= len(report_list):
                    n = 0
        sys.exit(0)

    def user(self, args: arguments):
        """Get information about the"""
        info = self.api.users("GET", args.action, args.id)
        autoformat(info, jsonfmt=args.json, table=True)
