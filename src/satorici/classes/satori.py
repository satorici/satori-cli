import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import requests
import yaml
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper

from satorici.classes.api import SatoriAPI
from satorici.classes.bundler import make_bundle
from satorici.classes.utils import (
    dict_formatter,
    filter_params,
    autoformat,
    check_monitor,
)


class Satori:
    """Have some class"""

    def __init__(self, profile="default", config=False):
        """Turn on the engines"""
        self.profile = profile
        self.config_paths = [
            f"{Path.home()}/.satori_credentials.yml",
            ".satori_credentials.yml",
        ]
        self.verbose = False
        if not config:
            self.load_config()
            self.api = SatoriAPI(self.token)

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
                print("Invalid config format")
                sys.exit(1)

            profile = config.get(self.profile)

            if not (profile and isinstance(profile, dict)):
                print("Invalid or non existent profile")
                profile_list = list(config.keys())
                print(f"Profiles list: {', '.join(profile_list)}")
                sys.exit(1)

            if not profile.get("token"):
                print(f"No token in profile: {self.profile}\n")
                print("satori-cli [-p PROFILE] config token TOKEN")
                sys.exit(1)

            self.config = config
            self.token = profile["token"]

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
                    print("Invalid config format")
                    sys.exit(1)
        else:
            config = {}
            config_file = self.config_paths[0]

        config.setdefault(self.profile, {})[key] = value

        with open(config_file, "w") as f:
            f.write(yaml.safe_dump(config))

        print("Token saved")

    def run(self, path):
        if os.path.isdir(path):
            self.run_folder(path)
        elif os.path.isfile(path):
            self.run_file(path)
        else:
            print("Unknown file type")  # is a device?
            sys.exit(1)

    def run_file(self, playbook):
        """Just run"""
        if playbook is None:
            print(
                f"Define the Satori playbook file:\n{sys.argv[0]} run -p playbook.yml"
            )
            return False

        if not os.path.isfile(playbook):
            print(f"Playbook not found: {playbook}")
            return False

        bundle = make_bundle(playbook)
        is_monitor = check_monitor(playbook)
        url = self.api.get_bundle_presigned_post()
        res = requests.post(url["url"], url["fields"], files={"file": bundle})
        if not res.ok:
            print("File upload failed")
            sys.exit(1)
        if is_monitor:
            print(f"Monitor ID: {url['monitor']}")
            print(f"Status: https://www.satori-ci.com/status?id={url['monitor']}")
        else:
            uuid = url["fields"]["key"].split("/")[1]
            print(f"UUID: {uuid}")
            print(f"Report: https://www.satori-ci.com/report_details/?n={uuid}")

    def run_folder(self, directory):
        """Upload directory and run"""
        if directory is None:
            print(
                "Define the directory with the Satori playbook:"
                f"\n{sys.argv[0]} run -p ./directory_with_playbook"
            )
            return False

        if not os.path.isdir(directory):
            print(f"Directory not found: {directory}")
            return False

        satori_yml = Path(directory, ".satori.yml")
        bundle = make_bundle(satori_yml, from_dir=True)
        is_monitor = check_monitor(satori_yml)
        temp_file = Path(tempfile.gettempdir(), str(uuid.uuid4()))
        full_path = f"{temp_file}.zip"

        try:
            shutil.make_archive(temp_file, "zip", directory)
        except Exception as e:
            print(f"Could not compress directory: {e}")
            return False

        res = self.api.get_archive_presigned_post()

        arc = res["archive"]
        bun = res["bundle"]

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

        res = requests.post(bun["url"], bun["fields"], files={"file": bundle})
        if not res.ok:
            print("Bundle upload failed")
            sys.exit(1)

        if is_monitor:
            print(f"Monitor ID: {bun['monitor']}")
            print(f"Status: https://www.satori-ci.com/status?id={bun['monitor']}")
        else:
            ruuid = bun["fields"]["key"].split("/")[1]
            print(f"UUID: {ruuid}")
            print(f"Report: https://www.satori-ci.com/report_details/?n={ruuid}")

    def repo(self, args):
        """Run Satori on multiple commits"""
        params = filter_params(args, ("id"))
        if args.action == "scan":
            params = filter_params(args, ("id", "coverage", "from", "to"))
        elif args.action == "clean":
            params = filter_params(args, ("id", "delete_commits"))
        elif args.action not in (
            "commits",
            "check-commits",
            "check-forks",
            "scan-stop",
            "scan-status",
            "run",
            "get",
        ):
            print("Unknown subcommand")
            sys.exit(1)
        info = self.api.repo_get(args.action, params)
        if args.action != "get" or args.json:
            autoformat(info, jsonfmt=args.json)
        else:
            print("Pending actions:")
            autoformat(info["pending"])
            print("\nRepos:")
            for monitor in info["list"]:
                autoformat(monitor, indent=1)
                print("  " + "-" * 48)

    def report(self, args):
        """Show a list of reports"""
        params = filter_params(args, ("id"))
        if args.action == "get":
            try:
                if uuid.UUID(args.id):
                    res = self.api.report_get(args.action, params)
                    autoformat(res, jsonfmt=args.json)
                    return
            except ValueError:
                pass

            params = filter_params(args, ("id", "page", "limit", "filters"))
            commits = self.api.report_get(args.action, params)
            for commit in commits:
                dict_formatter(commit)
                print(("_" * 48) + "\n")
            print(f"Current page: {args.page}")
        elif args.action == "output":
            self.output(args)
        elif args.action == "stop":
            res = self.api.report_stop(args.action, params)
            autoformat(res, jsonfmt=args.json)
        elif args.action == "delete":
            res = self.api.report_delete(params)
            autoformat(res, jsonfmt=args.json)
        else:
            print("Unknown subcommand")
            sys.exit(1)

    def monitor(self, args):
        """Get information about the"""
        params = filter_params(args, ("id"))
        if args.action == "delete":
            info = self.api.monitor_delete(params)
        elif args.action in ("start", "stop", "get"):
            info = self.api.monitor_get(args.action, params)
        else:
            print("Unknown subcommand")
            sys.exit(1)
        if args.action != "get" or args.json:
            autoformat(info, jsonfmt=args.json)
        else:
            print("Pending actions:")
            if len(info["pending"]) > 1:
                autoformat(info["pending"])
            else:
                print("  No active monitors defined")
            print("\nMonitors:")
            for monitor in info["list"]:
                autoformat(monitor, indent=1)
                print("  " + "-" * 48)

    def output(self, args, table: bool = True):
        """Returns commands output"""

        try:
            if uuid.UUID(args.id):
                data = self.api.get_report_output(args.id)
        except ValueError:
            sys.exit(1)

        if table:
            outputs = data.pop("output", [])
            for key, value in data.items():
                print(f"{key}: {value}")

            for row in outputs:
                print("-" * 30)
                for key, value in row.items():
                    print(f"{key}: {value}")
        else:
            print(json.dumps(data, indent=2))

    def dashboard(self, args):
        """Get user dashboard"""
        info = self.api.dashboard()
        if args.json:
            autoformat(info, jsonfmt=True)
        else:
            print("Actions required:")
            if len(info["Actions"]["Monitors"]) == 0:
                print("  Monitors: no active monitors defined")
            else:
                print("  Monitors:")
                autoformat(info["Actions"]["Monitors"], indent=1)
            if len(info["Actions"]["Repos"]) > 0:
                print("  Repos:")
                autoformat(info["Actions"]["Repos"], indent=1)
            for title in info:
                if title == "Actions":
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
        autoformat(data, jsonfmt=args.json)
