import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from zipfile import ZipFile

import requests
import yaml

from satorici.classes.api import SatoriAPI
from satorici.classes.bundler import make_bundle


class Satori():
    """Have some class"""
    def __init__(self, profile = "default", config = False):
        """Turn on the engines"""
        self.profile = profile
        self.config_paths = [
            f"{Path.home()}/.satori_credentials.yml",
            ".satori_credentials.yml"
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
            sys.exit(1)

        with config_file.open(encoding='utf-8') as f:
            config: dict[str, dict[str, str]] = yaml.safe_load(f)
            if not isinstance(config, dict):
                print("Invalid config format")
                sys.exit(1)

            profile = config.get(self.profile)

            if not (profile and isinstance(profile, dict)):
                print("Invalid or non existent profile")
                sys.exit(1)

            if not profile.get("token"):
                print(f"No token in profile: {self.profile}\n")
                print("satori-ci [-p PROFILE] config token TOKEN")
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

    def run(self, playbook):
        """Just run"""
        if playbook is None:
            print(f"Define the Satori playbook file:\n{sys.argv[0]} run -p playbook.yml")
            return False

        if not os.path.isfile(playbook):
            print(f"Playbook not found: {playbook}")
            return False

        bundle = make_bundle(playbook)
        res = self.api.get_bundle_presigned_post()
        requests.post(res["url"], res["fields"], files={"file": bundle})


    def upload(self, directory):
        """Upload directory and run"""
        if directory is None:
            print(f"Define the directory with the Satori playbook:\n{sys.argv[0]} run -p ./directory_with_playbook")
            return False

        if not os.path.isdir(directory):
            print(f"Directory not found: {directory}")
            return False

        bundle = make_bundle(Path(directory, ".satori.yml"))

        try:
            with tempfile.TemporaryFile() as f:
                with ZipFile(f, "w") as z:
                    for dirpath, dirnames, filenames in os.walk(directory):
                        for filename in filenames:
                            z.write(os.path.join(dirpath, filename))

                f.seek(0)
                data = f.read()
        except Exception as e:
            print(f"Could not compress directory: {e}")
            return False

        res = self.api.get_archive_presigned_post()

        arc = res["archive"]
        bun = res["bundle"]

        res = requests.post(arc["url"], arc["fields"], files={"file": data})
        if not res.ok:
            sys.exit(1)

        res = requests.post(bun["url"], bun["fields"], files={"file": bundle})
        if not res.ok:
            sys.exit(1)

    def report_status(self, id):
        """Show the status for a certain given report"""
        status = self.api.get_report_status(id)
        print(f"Status: {status['status']} | Fails: {status['fails']}")

    def cron_action(self, action, param):
        """TBC"""
        result = self.api.cron(action, param)
        if action == 'list':
            for cron in result:
                print(f"ID: {cron['ID']} | Name: {cron['display_name']}")
        elif action == 'stop':
            for cron in result:
                print(f"Stopped {cron['ID']}")

    def scan(self, repo_url, coverage, skip_check, from_date, to_date):
        """Run Satori on multiple commits"""
        params = {
            'repo': repo_url, 'coverage': coverage, 'skip_check': skip_check,
            'from': from_date, 'to': to_date}
        info = self.api.start_scan(params)
        for key in info:
            print(f"{key.capitalize()}: {info[key]}")

    def clean(self, repo, delete_commits):
        """Remove all reports (and commit information) from a repo"""
        params = {'repo': repo, 'delete_commits': delete_commits}
        res = self.api.clean_repo_info(params)
        print(res)

    def stop(self, obj_id):
        """Stop all scans in progress for a certain repo"""
        params = {'id': obj_id}
        stop_list = self.api.stop_scan(params)
        if isinstance(stop_list, dict):
            stop_list = [stop_list]
        for stop in stop_list:
            for key in stop:
                print(f"{key}:")
            for obj in stop[key]:
                print(obj)

    def scan_info(self, repo):
        """Get information about the """
        params = {'repo': repo}
        info = self.api.get_scan_info(params)
        for key in info:
            print(f"{key.capitalize()}: {info[key]}")

    def ci(self):
        """Get information about the """
        params = {}
        info = self.api.get_ci_info(params)
        for repo in info:
            for key in repo:
                print(f"{key}: {repo[key]}")
            print("-"*48)

    def report_info(self, repo, page, limit, filters):
        """Show a list of reports"""
        try:
            if uuid.UUID(repo):
                res = self.api.get_report_json(repo)
                print(res)
                return
        except ValueError:
            pass

        params = {'repo': repo, 'page': page, 'limit': limit, 'filters': filters}
        commits = self.api.get_report_info(params)
        for commit in commits:
            for key in commit:
                if key == 'Report':
                    print("▢ Report:")
                    for report_key in commit['Report']:
                        if report_key == 'Satori Error' and commit['Report']['Satori Error'] is not None:
                            print("  • Satori Error:")
                            split_msg = commit['Report']['Satori Error'].split("\n")
                            for msg in split_msg:
                                print(f"   ░ {msg}")
                        elif report_key == 'Testcases':
                            print("  • Testcases:")
                            for testcase in commit['Report']['Testcases']:
                                print(f"    ○ {testcase}")
                        else:
                            print(f"  • {report_key}: {commit['Report'][report_key]}")
                else:
                    print(f"▢ {key}: {commit[key]}")
            print(("_" * 48)+"\n")
        print(f"Current page: {page}")

    def monitor(self):
        """Get information about the """
        params = {}
        info = self.api.get_monitor_info(params)
        for repo in info:
            for key in repo:
                print(f"{key}: {repo[key]}")
            print("-"*48)

    def output(self, id: str, table: bool = True):
        """Returns commands output"""

        try:
            if uuid.UUID(id):
                data = self.api.get_report_output(id)
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
