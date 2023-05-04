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
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper
from colorama import Fore

from satorici.classes.api import SatoriAPI
from satorici.classes.bundler import make_bundle
from satorici.classes.utils import (
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
)


class Satori:
    """Have some class"""

    def __init__(self, args, config=False):
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

    def load_config(self):
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

    def run(self, args):
        exec_data = None
        if os.path.isdir(args.path):
            exec_data = self.run_folder(args)
        elif os.path.isfile(args.path):
            exec_data = self.run_file(args)
        else:
            puts(FAIL_COLOR, "Unknown file type")  # is a device?
            sys.exit(1)
        if args.sync and exec_data:
            self.run_sync(exec_data)

    def run_file(self, args) -> dict:
        """Just run"""
        playbook = args.path
        if playbook is None:
            print(
                f"Define the Satori playbook file:\n{sys.argv[0]} run -p playbook.yml"
            )
            return False

        if not os.path.isfile(playbook):
            puts(FAIL_COLOR, f"Playbook not found: {playbook}")
            return False

        bundle = make_bundle(playbook)
        is_monitor = check_monitor(playbook)
        url = self.api.get_bundle_presigned_post(args)
        res = requests.post(
            url["url"],
            url["fields"],
            files={"file": bundle},
        )
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

    def run_folder(self, args) -> dict:
        """Upload directory and run"""
        directory = args.path
        if directory is None:
            print(
                "Define the directory with the Satori playbook:"
                f"\n{sys.argv[0]} run -p ./directory_with_playbook"
            )
            return False

        if not os.path.isdir(directory):
            puts(FAIL_COLOR, f"Directory not found: {directory}")
            return False

        satori_yml = Path(directory, ".satori.yml")
        bundle = make_bundle(satori_yml, from_dir=True)
        is_monitor = check_monitor(satori_yml)
        temp_file = Path(tempfile.gettempdir(), str(uuid.uuid4()))
        full_path = f"{temp_file}.zip"

        try:
            shutil.make_archive(temp_file, "zip", directory)
        except Exception as e:
            puts(FAIL_COLOR, f"Could not compress directory: {e}")
            return False

        res = self.api.get_archive_presigned_post(args)

        arc = res["archive"]
        bun = res["bundle"]
        mon = res["monitor"]

        try:
            bar_params = {
                "total": os.stat(full_path).st_size,
                "unit": "B",
                "desc": "Archive upload",
                "unit_scale": True,
            }
            with tqdm(**bar_params) as t, open(full_path, "rb") as f:
                w = CallbackIOWrapper(t.update, f, "read")
                res = requests.post(arc["url"], arc["fields"], files={"file": w})
        finally:
            os.remove(full_path)

        if not res.ok:
            print("Archive upload failed")
            sys.exit(1)

        res = requests.post(
            bun["url"],
            bun["fields"],
            files={"file": bundle},
        )
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

    def run_sync(self, exec_data: dict) -> None:
        puts(KEYNAME_COLOR, "Fetching data...", end="\r")
        start_time = time.time()
        while True:
            time.sleep(1)
            elapsed = time.time() - start_time
            elapsed_text = f"Elapsed time: {elapsed:.1f}s"
            try:
                report_data = self.api.report_get("get", {"id": exec_data["id"]})
            except requests.HTTPError as e:
                code = e.response.status_code
                if code in (404, 403):
                    print(
                        autocolor(f"Report status: Unknown | {elapsed_text}"), end="\r"
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
                        f"Report status: {status} | Result: {result} | {elapsed_text}"
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
                print(autocolor(f"Report status: {status} | {elapsed_text}"), end="\r")

    def repo(self, args):
        """Run Satori on multiple commits"""
        params = filter_params(args, ("id"))
        if args.playbook:
            playbook = Path(args.playbook)
            if playbook.is_file():
                args.playbook = playbook.read_text()
        if args.action == "scan":
            params = filter_params(
                args, ("id", "coverage", "from", "to", "branch", "data", "playbook")
            )
        elif args.action == "clean":
            params = filter_params(args, ("id", "delete_commits"))
        elif args.action == "tests":
            params = filter_params(args, ("id", "filter", "all", "limit", "fail"))
        elif args.action == "run":
            params = filter_params(args, ("id", "data", "playbook"))
        elif args.action == "check-commits":
            params = filter_params(args, ("id", "branch"))
        elif args.action not in (
            "commits",
            "check-forks",
            "scan-stop",
            "scan-status",
            "get",
            "download",
            "pending"
        ):
            print("Unknown subcommand")
            sys.exit(1)
        info = self.api.repo_get(args, params)
        if args.id != "list" or args.action != "get" or args.json:
            autoformat(info, jsonfmt=args.json, list_separator="-" * 48)
        else:
            print("Pending actions:")
            autoformat(info["pending"])
            print("\nRepos:")
            autoformat(info["list"], list_separator="-" * 48)
        if args.action == "run" and args.sync:
            if isinstance(info, list):
                info = info[0]
            report = info.get("status", "")
            match = UUID4_REGEX.findall(report)
            if match:
                self.run_sync({"type": "report", "id": match[0]})

    def report(self, args):
        """Show a list of reports"""
        params = filter_params(args, ("id"))
        if args.action == "get":
            params = filter_params(args, ("id", "page", "limit", "filter"))
            res = self.api.report_get(args, params)
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
            res = self.api.report_get(args, params)
            autoformat(res, jsonfmt=args.json)
        elif args.action == "delete":
            self.api.report_delete(params)
            print("Report deleted")
        else:
            print("Unknown subcommand")
            sys.exit(1)

    def monitor(self, args):
        """Get information about the"""
        params = filter_params(args, ("id"))
        if args.action == "delete":
            self.api.monitor_delete(params)
            print("Monitor deleted")
            sys.exit(0)
        elif args.action in ("start", "stop", "get"):
            info = self.api.monitor_get(args, params)
        else:
            print("Unknown subcommand")
            sys.exit(1)
        if args.id != "list" or args.action != "get" or args.json:
            autoformat(info, jsonfmt=args.json, list_separator="*" * 48)
        else:
            if len(info["pending"]) > 1:
                print("Pending actions:")
                autoformat(info["pending"])
            print("\nMonitors:")
            autoformat(info["list"], list_separator="-" * 48)

    def output(self, args, params):
        """Returns commands output"""

        try:
            if uuid.UUID(args.id):
                data = self.api.report_get(args, params)
        except ValueError:
            sys.exit(1)

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

    def dashboard(self, args):
        """Get user dashboard"""
        info = self.api.dashboard()
        if args.json:
            autoformat(info, jsonfmt=True)
        else:
            len_mon = len(info["Actions"]["Monitors"])
            len_rep = len(info["Actions"]["Repos"])
            if len_mon > 0 or len_rep > 0:
                print("Actions required:")
                if len_mon > 0:
                    print("  Monitors:")
                    autoformat(info["Actions"]["Monitors"], indent=1)
                if len_rep > 0:
                    print("  Repos:")
                    autoformat(info["Actions"]["Repos"], indent=1)
            for title in info:
                if title == "Actions":
                    continue
                if title == "Monitors":
                    if len(info[title]) == 0:
                        print("\nMonitors: no active monitors defined")
                        continue
                print(f"\n{title}:")
                n = 0
                for i in info[title]:
                    n += 1
                    for key in i:
                        print(f"{n}) {key.capitalize()}: {i[key]}")

    def playbook(self, args):
        """Get playbooks"""
        if args.action == "get":
            params = filter_params(args, ("id", "limit", "page"))
            data = self.api.playbook_get(params)
            if args.json:
                print(json.dumps(data))
                sys.exit(1)
            if args.id == "all":
                data = list(
                    map(
                        lambda x: {
                            "ID": x["ID"],
                            "URI": x["URI"],
                            "Name": x["Name"],
                            # Add a new line to remove indent
                            "Playbook": f"\n{x['Playbook']}",
                        },
                        data,
                    )
                )
        elif args.action == "delete":
            params = filter_params(args, ("id"))
            data = self.api.playbook_delete(params)
        else:
            print("Unknown subcommand")
            sys.exit(1)
        autoformat(data, jsonfmt=args.json, list_separator="-" * 48)

    def team(self, args):
        """Get information about the"""
        params = filter_params(args, ("id"))
        if args.action == "get":
            info = self.api.team_get(params)
        elif args.action == "create":
            info = self.api.team_post(params)
        elif args.action == "members":
            info = self.api.team_members_get(params)
        elif args.action == "add_member":
            params = filter_params(args, ("id", "email", "role"))
            info = self.api.team_members_put(params)
        elif args.action == "repos":
            info = self.api.team_repos_get(params)
        elif args.action == "add_repo":
            params = filter_params(args, ("id", "repo"))
            info = self.api.team_repos_put(params)
        else:
            print("Unknown subcommand")
            sys.exit(1)
        autoformat(info, jsonfmt=args.json, list_separator="*" * 48)
