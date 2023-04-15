import requests
import sys
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

HOST = "https://api.satori-ci.com"


class SatoriAPI:
    def __init__(self, token: str, server: str, cli_args):
        self.__session__ = requests.Session()
        self.__session__.headers.update(
            Authorization=f"Bearer {token}",
        )
        self.timeout = cli_args.timeout
        self.debug = cli_args.debug
        self.__session__.hooks = {
            "response": lambda r, *args, **kwargs: r.raise_for_status()
        }
        self.server = server or HOST

    def request(self, method: str, endpoint: str, **kwargs):
        try:
          resp = self.__session__.request(
              method=method,
              url=f"{self.server}/{endpoint}",
              timeout=self.timeout,
              **kwargs,
          )
        except:
          puts(FAIL_COLOR, "Connection error")
          sys.exit(1)
        if self.debug:
            print(resp.headers)
        return resp

    def debug_bridge(self, res: requests.Response, args) -> dict:
        if args.debug:
            print("Response headers:", res.headers)
        return res.json()

    def get_bundle_presigned_post(self, args):
        res = self.request("GET", "run/bundle", data={"secrets": args.data})
        return res.json()

    def get_archive_presigned_post(self, args):
        res = self.request("GET", "run/archive", data={"secrets": args.data})
        return res.json()

    def repo_get(self, args, parameters):
        if args.action == "get":
            args.action = ""
        res = self.request("GET", f"repo/{args.action}", params=parameters)
        return res.json()

    def monitor_get(self, action, parameters):
        if action == "get":
            action = ""
        res = self.request("GET", f"monitor/{action}", params=parameters)
        return res.json()

    def monitor_delete(self, parameters):
        res = self.request("DELETE", "monitor", params=parameters)
        return res.json()

    def report_get(self, action, parameters):
        if action == "get":
            action = ""
        res = self.request("GET", "report/{action}", params=parameters)
        return res.json()

    def report_delete(self, parameters):
        res = self.request("DELETE", "report", params=parameters)
        return res.json()

    def dashboard(self):
        res = self.request("GET", "dashboard")
        return res.json()

    def playbook_get(self, parameters):
        res = self.request("GET", "playbook", params=parameters)
        return res.json()

    def playbook_delete(self, parameters):
        res = self.request("DELETE", "playbook", params=parameters)
        return res.json()

    def team_get(self, parameters):
        res = self.request("GET", "team", params=parameters)
        return res.json()

    def team_post(self, parameters):
        res = self.request("POST", "team", params=parameters)
        return res.json()

    def team_members_get(self, parameters):
        res = self.request("GET", "team/members", params=parameters)
        return res.json()

    def team_members_put(self, parameters):
        res = self.request("PUT", "team/members", params=parameters)
        return res.json()

    def team_repos_get(self, parameters):
        res = self.request("GET", "team/repos", params=parameters)
        return res.json()

    def team_repos_put(self, parameters):
        res = self.request("PUT", "team/repos", params=parameters)
        return res.json()
