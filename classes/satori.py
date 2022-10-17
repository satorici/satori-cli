import io
import logging
import mimetypes
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
    def __init__(self):
        """Turn on the engines"""
        self.verbose = False
        self.config_data = {}
        user_home = Path.home()
        # self.config_path = [f"{user_home}/.satori_credentials.json", ".satori_credentials.json"]
        self.config_path = [f"{user_home}/.satori_credentials.yml", ".satori_credentials.yml"]
        self.host = "https://w7zcm8h3h1.execute-api.us-east-2.amazonaws.com/staging/"  # TODO: api.satori-ci.com
        self.api_host = "https://nuvyp2kffa.execute-api.us-east-2.amazonaws.com/"
        self.headers = {}

    def load_config(self, profile='default', create_profile=False):
        """Load the config file and set the token on the headers"""
        config_file = None
        if os.path.isfile(self.config_path[0]):
            config_file = Path(self.config_path[0])
        elif os.path.isfile(self.config_path[1]):
            config_file = Path(self.config_path[1])
        elif create_profile:
            self.config_data = {profile:{'token':''}}
            return
        else:
            print("Config file not found")
        if config_file:
            with config_file.open(encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
        # Check if user token exist
        token = None
        if profile in self.config_data:
            token = self.config_data[profile]['token']
        else:
            for first_profile in self.config_data:
                print(f"Warning: {profile} token not found, using profile {first_profile}")
                token = self.config_data[first_profile]['token']
                break
        if token:
            self.headers = {"Authorization": f"token {token}"}
        else:
            print(f"Set a token with: {sys.argv[0]} config default \"your_user_token\"")
            print("How to get a Satori CI Token: TBC")
            sys.exit(1)

    def save_config(self, profile: str, value: str):
        """Save the token into the config file"""
        if value == "":
            print("Value not defined")
            return False
        self.load_config(profile=profile, create_profile=True)
        if profile:
            self.config_data[profile] = {}
            self.config_data[profile]['token'] = value
            config_yaml = yaml.dump(self.config_data)
            try:
                file = open(self.config_path[0], 'w', 0o700, encoding='utf-8')
            except PermissionError:
                print("Warning: the token file could not be saved in $HOME, using current directory")
                file = open(self.config_path[1], 'w', 0o700, encoding='utf-8')
            file.write(config_yaml)
            file.close()
            print(f'Config token updated for: {profile}')
        return True

    def mime_type(self, playbook):
        """Get mime type"""
        mime_type = None
        file_name = os.path.splitext(playbook)
        if file_name[1] == '.yml':
            mime_type = 'application/x-yaml'
        elif mime_type is None:
            mime_type = mimetypes.guess_type('playbook.zip')[0]
        return mime_type

    def run(self, playbook, profile):
        """Just run"""
        self.load_config(profile=profile)
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
                zip_file.write(playbook, "satori.yml")
                for key, paths in references.items():
                    for path in paths:
                        zip_file.write(Path(playbook_dir, path), Path(key, path))
        except Exception as e:
            logging.error(e)
            return False
        playbook = "SatoriBundle.zip"
        headers = {
            "Authorization": f"token {self.config_data[profile]['token']}",
            "Content-Type": "application/zip",
            "X-File-Name": playbook,
        }
        try:
            response = self.connect("POST", f"{self.host}", playbook=playbook, data=bundle.getvalue(), headers=headers)  # TODO: endpoint TBD
        except KeyboardInterrupt:
            sys.exit(0)
        if response.status_code == 200:
            status = response.json()
            print(f"UUID: {status['uuid']} | URL: {status['report_url']}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def upload(self, directory, profile):
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

        try:
            response = self.connect("POST", f"{self.host}", playbook=directory, data=data, profile=profile)  # TODO: endpoint TBD
        except KeyboardInterrupt:
            sys.exit(0)
        if response.status_code == 200:
            status = response.json()
            print(f"UUID: {status['uuid']} | URL: {status['report_url']}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def connect(self, method, endpoint, playbook=None, data=None, headers=None, profile='default'):
        """Connect to the Satori API"""
        self.load_config(profile=profile)
        if headers is None:
            headers = self.headers
        response = None
        if self.verbose is True:
            print("method:", method, " - endpoint:", endpoint, " - playbook:", playbook, " - headers:", headers)
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

    def playbooks(self, profile):
        """List playbooks for the user"""
        response = self.connect("GET", f"{self.host}", profile=profile)  # TODO: endpoint TBD

    def stop_report(self, id, profile):
        """Stop the execution of a certain given report"""
        response = self.connect("GET", f"{self.api_host}report/stop/{id}", profile=profile)
        if response.status_code == 200:
            status = response.json()
            print(f"Stopped status: {status['status']}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def report_status(self, id, profile):
        """Show the status for a certain given report"""
        response = self.connect("GET", f"{self.api_host}report/status/{id}", profile=profile)
        if response.status_code == 200:
            status = response.json()
            print(f"Status: {status['status']} | Fails: {status['fails']}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def cron_action(self, action, param, profile):
        """TBC"""
        response = self.connect("GET", f"{self.api_host}cron/{action}/{param}", profile=profile)
        if response.status_code == 200:
            if action == 'list':
                for cron in response.json():
                    print(f"ID: {cron['ID']} | Name: {cron['display_name']}")
            elif action == 'stop':
                for cron in response.json():
                    print(f"Stopped {cron['ID']}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def scan(self, repo_url, coverage, skip_check, from_date, to_date, profile):
        """Run Satori on multiple commits"""
        params = urlencode(
            {'repo': repo_url, 'coverage': coverage, 'skip_check': skip_check,
            'from': from_date, 'to': to_date},
            quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}scan/start?{params}", profile=profile)
        if response.status_code == 200:
            info = response.json()
            for key in info:
                print(f"{key.capitalize()}: {info[key]}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def clean(self, repo, delete_commits, profile):
        """Remove all reports (and commit information) from a repo"""
        params = urlencode({'repo': repo, 'delete_commits': delete_commits}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}scan/clean?{params}", profile=profile)
        print(f"{response.status_code = }\n{response.text = }")

    def stop(self, repo, profile):
        """Stop all scans in progress for a certain repo"""
        params = urlencode({'repo': repo}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}stop?{params}", profile=profile)
        print(f"{response.status_code = }\n{response.text = }")

    def scan_info(self, repo, profile):
        """Get information about the """
        params = urlencode({'repo': repo}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}info?{params}", profile=profile)
        if response.status_code == 200:
            info = response.json()
            for key in info:
                print(f"{key.capitalize()}: {info[key]}")
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def ci(self, profile):
        """Get information about the """
        params = urlencode({}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}ci?{params}", profile=profile)
        if response.status_code == 200:
            info = response.json()
            for repo in info:
                for key in repo:
                    print(f"{key}: {repo[key]}")
                print("-"*48)
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def report_info(self, repo, page, limit, filters, profile):
        """Show a list of reports"""
        try:
            if uuid.UUID(repo):
                res = self.connect("GET", f"{self.api_host}report/info/{repo}", profile=profile)
                print(res.text)
                return
        except ValueError:
            pass

        params = urlencode({'repo': repo, 'page': page, 'limit': limit, 'filters': filters}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}report/info?{params}", profile=profile)
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

    def monitor(self, profile):
        """Get information about the """
        params = urlencode({}, quote_via=quote_plus)
        response = self.connect("GET", f"{self.api_host}monitor?{params}", profile=profile)
        if response.status_code == 200:
            info = response.json()
            for repo in info:
                for key in repo:
                    print(f"{key}: {repo[key]}")
                print("-"*48)
        else:
            print(f"{response.status_code = }\n{response.text = }")

    def output(self, profile: str, id: str):
        """Returns commands output"""

        try:
            if uuid.UUID(id):
                res = self.connect("GET", f"{self.api_host}report/output/{id}", profile=profile)
                print(res.text)
                return
        except ValueError:
            pass
