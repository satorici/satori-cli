import ast
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
import time
import requests
import yaml
from rich.progress import open as progress_open
from colorama import Fore
from satorici.validator import validate_playbook

from .api import SatoriAPI
from .bundler import make_bundle
from .utils import (
    dict_formatter,
    filter_params,
    autoformat,
    check_monitor,
    FAIL_COLOR,
    KEYNAME_COLOR,
    SATORIURL_COLOR,
    VALUE_COLOR,
    UUID4_REGEX,
    autocolor,
    puts,
    log,
    autotable,
    console,
    UNKNOWN_COLOR,
)
from .validations import get_parameters, validate_parameters
from .playbooks import display_public_playbooks
from .data import arguments


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

        with open(config_file, "w") as f:
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
            puts(FAIL_COLOR, "Satori can not access to file/folder")
            sys.exit(1)

        playbook_text = playbook.read_text()
        try:
            config = validate_playbook(yaml.safe_load(playbook_text))
            variables = get_parameters(config)
        except yaml.YAMLError as e:
            console.log(
                f"Error parsing the playbook [bold]{playbook.name}[/bold]:\n", e
            )
            sys.exit(1)
        except Exception as e:
            console.log(
                f"Validation error on playbook [bold]{playbook.name}[/bold]:\n", e
            )
            sys.exit(1)

        if variables - params:
            puts(FAIL_COLOR, f"Required parameters: {variables - params}")
            sys.exit(1)

        if path.is_dir():
            exec_data = self.run_folder(args)
        else:  # is file
            exec_data = self.run_file(args)
        if args.sync and exec_data:
            self.run_sync(exec_data)

    def run_file(self, args: arguments) -> dict:
        """Just run"""
        playbook = args.path
        bundle = make_bundle(playbook)
        is_monitor = check_monitor(playbook)
        url = self.api.runs("bundle", {"secrets": args.data})
        log.debug(url)
        res = requests.post(
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
            print(KEYNAME_COLOR + "UUID: " + VALUE_COLOR + f"{exec_id}")
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
        full_path = f"{temp_file}.zip"

        try:
            shutil.make_archive(str(temp_file), "zip", directory)
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
                res = requests.post(
                    arc["url"], arc["fields"], files={"file": f}, timeout=None
                )
        finally:
            os.remove(full_path)

        if not res.ok:
            print("Archive upload failed")
            sys.exit(1)

        res = requests.post(
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
            print(KEYNAME_COLOR + "UUID: " + VALUE_COLOR + f"{exec_id}")
            print(
                autocolor(
                    f"Report: https://www.satori-ci.com/report_details/?n={exec_id}"
                )
            )
        return {"type": exec_type, "id": exec_id}

    def run_url(self, args: arguments):
        info = self.api.runs("url", {"secrets": args.data, "url": args.path})
        autoformat({"Running with the ID": info.get("report_id")}, jsonfmt=args.json)
        if args.sync:
            exec_data = {"type": "report", "id": info["report_id"]}
            self.run_sync(exec_data)
        sys.exit(0)

    def run_sync(self, exec_data: dict) -> None:
        if exec_data["type"] == "monitor":
            puts(UNKNOWN_COLOR, "Sync mode is not supported for monitors")
            sys.exit(0)
        puts(KEYNAME_COLOR, "Fetching data...", end="\r")
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
                    puts(FAIL_COLOR, f"Failed to get data\nStatus code: {code}")
                    sys.exit(1)

            status = report_data.get("status", "Unknown")
            if status in ("Completed", "Undefined"):
                fails = report_data["fails"]
                if fails is None:
                    result = "Unknown"
                else:
                    result = "Pass" if fails == 0 else f"Fail({fails})"
                print(
                    autocolor(
                        f"- Report status: {status} | Result: {result} | {elapsed_text}"
                    ),
                    end="\r\n",
                )
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
                if status == "Undefined":
                    comments = report_data.get("comments")
                    if comments:
                        puts(FAIL_COLOR, f"Error: {comments}")
                    sys.exit(1)
                else:
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
            console.rule("[b green]Repos", style="green")
            autotable(info["list"], "bold blue", widths=(None, 10, 12, 20, 10, 40))
        if args.action == "run" and args.sync:
            if isinstance(info, list):
                info = info[0]
            report = info.get("status", "")
            match = UUID4_REGEX.findall(report)
            if match:
                self.run_sync({"type": "report", "id": match[0]})

    def report(self, args: arguments):
        """Show a list of reports"""
        params = filter_params(args, ("id",))
        if args.action == "":
            params = filter_params(args, ("id", "page", "limit", "filter"))
            res = self.api.reports("GET", args.id, "", params=params)
            if isinstance(res, list) and not args.json:
                for commit in res:
                    dict_formatter(commit)
                    puts(Fore.LIGHTBLACK_EX, ("_" * 48) + "\n")
            else:
                autoformat(res, jsonfmt=args.json)
            if not args.json:
                print(f"Current page: {args.page}")
        elif args.action == "output":
            self.output(args, params)
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
            self.api.monitor_delete(params)
            print("Monitor deleted")
            sys.exit(0)
        elif args.action == "":
            info = self.api.monitors("GET", args.id, "")
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

    def output(self, args: arguments, params):
        """Returns commands output"""
        data = self.api.reports("GET", args.id, args.action, params=params)

        if not args.json:  # default output
            outputs = data.pop("output", [])
            for key, value in data.items():
                print(f"{key}: {value}")

            for row in outputs:
                puts(Fore.LIGHTBLACK_EX, "-" * 48)
                puts(Fore.CYAN, f"test_name: {row['test_name']}")
                puts(KEYNAME_COLOR, "command: ", Fore.LIGHTBLUE_EX, row["command"])
                for key, value in row.items():
                    if key in ("test_name", "command"):
                        continue
                    val_color = VALUE_COLOR
                    if key == "stdout":
                        val_color = Fore.LIGHTGREEN_EX
                    elif key == "stderr":
                        val_color = Fore.LIGHTRED_EX
                    elif key == "return_code":
                        val_color = Fore.YELLOW
                    puts(KEYNAME_COLOR, f"{key}: ", val_color, str(value))
        else:
            print(json.dumps(data, indent=2))

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
                        "[b][blue]Monitors[/blue](Actions required)", style="white"
                    )
                    autotable(
                        info["monitors"]["pending"], "b blue", widths=(20, 20, None)
                    )
                if len_rep > 0:
                    console.rule(
                        "[b][green]Repos[/green](Actions required)", style="white"
                    )
                    autotable(info["repos"]["pending"], "b green", widths=(50, 50))
            if len(info["monitors"]["list"]) == 0:
                console.log("[b]Monitors:[red] no active monitors defined")
            else:
                console.rule("[b blue]Monitors", style="blue")
                autotable(info["monitors"]["list"], "b blue", True)
            if len(info["repos"]["list"]) > 0:
                console.rule("[b green]Repos", style="green")
                autotable(
                    info["repos"]["list"],
                    "b green",
                    True,
                    widths=(3, None, 10, 12, 20, 10, 40),
                )

    def playbook(self, args: arguments):
        """Get playbooks"""
        if args.public:
            display_public_playbooks()

        if args.action == "":
            params = filter_params(args, ("id", "limit", "page"))
            data = self.api.playbook_get(params)
            if args.json:
                autoformat(data, jsonfmt=True)
                sys.exit(1)
        elif args.action == "delete":
            params = filter_params(args, ("id",))
            data = self.api.playbook_delete(params)
        else:
            print("Unknown subcommand")
            sys.exit(1)
        autoformat(data, jsonfmt=args.json, list_separator="-" * 48)

    def team(self, args: arguments):
        """Get information about the"""
        params = filter_params(args, ("id",))
        if args.action == "":
            info = self.api.teams("GET", "", "", params=params)
        elif args.action == "create":
            info = self.api.teams("PUT", args.id, "", data=params)
        elif args.action == "members":
            info = self.api.teams("GET", args.id, "members", params=params)
        elif args.action == "add_member":
            params = filter_params(args, ("id", "email", "role"))
            info = self.api.teams("PUT", args.id, "members", data=params)
        elif args.action == "repos":
            info = self.api.teams("PUT", args.id, "repos", data=params)
        elif args.action == "add_repo":
            params = filter_params(args, ("id", "repo"))
            info = self.api.teams("PUT", args.id, "repos", data=params)
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
                        console.log(f"[bold]{repo}[/bold] [red]Failed to start")
                        completed.append(repo)
                    try:
                        report_data = self.api.reports(
                            "GET", report, "", raise_error=True
                        )
                    except requests.HTTPError as e:
                        code = e.response.status_code
                        if code not in (404, 403):
                            console.log(f"[red]Failed to get data\nStatus code: {code}")
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
                            console.log(
                                f"[bold]{repo}[/bold] Completed | Result: {result}"
                            )
                            completed.append(repo)
                time.sleep(0.5)
                n += 1
                if n >= len(report_list):
                    n = 0
        sys.exit(0)
