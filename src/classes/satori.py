import io
import json
import logging
import os
import shutil
import sys
import uuid
from pathlib import Path
from urllib.parse import quote_plus, urlencode
from zipfile import ZipFile

import requests
import yaml

from classes.resolver import get_references


class Satori():
    """Have some class"""
    def __init__(self, profile = "default", config = False):
        """Turn on the engines"""
        self.profile = profile
        self.config_paths = [
            f"{Path.home()}/.satori_credentials.yml",
            ".satori_credentials.yml"
        ]
        # TODO: api.satori-ci.com
        self.host = "https://w7zcm8h3h1.execute-api.us-east-2.amazonaws.com/staging/"
        self.api_host = "https://nuvyp2kffa.execute-api.us-east-2.amazonaws.com/"
        self.verbose = False
        if not config:
            self.load_config()


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

        bundle = io.BytesIO()

        try:
            with open(playbook, encoding='utf-8') as f, ZipFile(bundle, "x") as zip_file:
                playbook_dir = os.path.dirname(playbook)
                references = get_references(f.read(), playbook_dir)
                zip_file.write(playbook, ".satori.yml")
                for key, paths in references.items():
                    for path in paths:
                        zip_file.write(Path(playbook_dir, path), Path(key, path))
        except Exception as e:
            logging.error(e)
            return False
        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "satori/bundle_zip", # is always a zip?
            "X-File-Name": playbook,
        }
        try:
            response = self.connect("POST", f"{self.host}", data=bundle.getvalue(), headers=headers)  # TODO: endpoint TBD
        except KeyboardInterrupt:
            sys.exit(0)
        if response.status_code == 200:
            status = response.json()
            for key in status:
                print(f"{key}: {status[key]}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def upload(self, directory):
        """Upload directory and run"""
        temp_file = "plbk-" + str(uuid.uuid4())
        if directory is None:
            print(f"Define the directory with the Satori playbook:\n{sys.argv[0]} run -p ./directory_with_playbook")
            return False

        if os.path.isdir(directory):
            shutil.make_archive(temp_file, 'zip', directory)
            with open(temp_file + '.zip', 'rb') as f:
                data = f.read()
            os.remove(temp_file + '.zip')
        else:
            print(f"Directory not found: {directory}")
            return False

        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "satori/bundle_zip", # is always a zip?
            "X-File-Name": 'Directory'
        }

        try:
            response = self.connect("POST", f"{self.host}", data=data, headers=headers)  # TODO: endpoint TBD
        except KeyboardInterrupt:
            sys.exit(0)
        if response.status_code == 200:
            status = response.json()
            for key in status:
                print(f"{key}: {status[key]}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def connect(self, method, endpoint, data=None, headers=None):
        """Connect to the Satori API"""
        if headers is None:
            headers = {"Authorization": f"token {self.token}"}
        response = None
        if self.verbose:
            print("method:", method, " - endpoint:", endpoint, " - headers:", headers)
        if method == "POST":
            try:
                response = requests.post(endpoint, data=data, headers=headers)
            except requests.exceptions.ConnectionError:
                logging.error("Connection could not be open")
            except KeyboardInterrupt:
                sys.exit(0)
        elif method == "GET":
            try:
                response = requests.get(endpoint, headers=headers)
            except requests.exceptions.ConnectionError:
                logging.error("Connection could not be open")
            except KeyboardInterrupt:
                sys.exit(0)
        if response is not None:
            return response
        sys.exit(1)

    def playbooks(self):
        """List playbooks for the user"""
        response = self.connect("GET", f"{self.host}")  # TODO: endpoint TBD

    def report_status(self, id):
        """Show the status for a certain given report"""
        response = self.connect("GET", f"{self.api_host}report/status/{id}")
        if response.status_code == 200:
            status = response.json()
            print(f"Status: {status['status']} | Fails: {status['fails']}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def cron_action(self, action, param):
        """TBC"""
        response = self.connect("GET", f"{self.api_host}cron/{action}/{param}")
        if response.status_code == 200:
            if action == 'list':
                for cron in response.json():
                    print(f"ID: {cron['ID']} | Name: {cron['display_name']}")
            elif action == 'stop':
                for cron in response.json():
                    print(f"Stopped {cron['ID']}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def scan(self, repo_url, coverage, skip_check, from_date, to_date):
        """Run Satori on multiple commits"""
        params = urlencode(
            {'repo': repo_url, 'coverage': coverage, 'skip_check': skip_check,
            'from': from_date, 'to': to_date},
            quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}scan/start?{params}")
        if response.status_code == 200:
            info = response.json()
            for key in info:
                print(f"{key.capitalize()}: {info[key]}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def clean(self, repo, delete_commits):
        """Remove all reports (and commit information) from a repo"""
        params = urlencode({'repo': repo, 'delete_commits': delete_commits}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}scan/clean?{params}")
        print(f"{response.status_code = }\n{response.text = }")

    def stop(self, obj_id):
        """Stop all scans in progress for a certain repo"""
        params = urlencode({'id': obj_id}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}stop?{params}")
        if response.status_code == 200:
            stop_list = response.json()
            if isinstance(stop_list, dict):
                stop_list = [stop_list]
            for stop in stop_list:
                for key in stop:
                    print(f"{key}:")
                for obj in stop[key]:
                    print(obj)
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def scan_info(self, repo):
        """Get information about the """
        params = urlencode({'repo': repo}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}info?{params}")
        if response.status_code == 200:
            info = response.json()
            for key in info:
                print(f"{key.capitalize()}: {info[key]}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def ci(self):
        """Get information about the """
        params = urlencode({}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}ci?{params}")
        if response.status_code == 200:
            info = response.json()
            for repo in info:
                for key in repo:
                    print(f"{key}: {repo[key]}")
                print("-"*48)
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def report_info(self, repo, page, limit, filters):
        """Show a list of reports"""
        try:
            if uuid.UUID(repo):
                res = self.connect("GET", f"{self.api_host}report/info/{repo}")
                print(res.text)
                return
        except ValueError:
            pass

        params = urlencode({'repo': repo, 'page': page, 'limit': limit, 'filters': filters}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}report/info?{params}")
        if response.status_code == 200:
            commits = response.json()
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
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def monitor(self):
        """Get information about the """
        params = urlencode({}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}monitor?{params}")
        if response.status_code == 200:
            info = response.json()
            for repo in info:
                for key in repo:
                    print(f"{key}: {repo[key]}")
                print("-"*48)
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def output(self, id: str, table: bool = True):
        """Returns commands output"""

        try:
            if uuid.UUID(id):
                res = self.connect("GET", f"{self.api_host}report/output/{id}")
                if not res.ok:
                    print("Could not fetch output")
                    sys.exit(1)
        except ValueError:
            sys.exit(1)

        data: dict = res.json()

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
