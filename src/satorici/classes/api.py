import requests
import sys
from requests import Response
from requests.exceptions import ConnectionError, ReadTimeout, HTTPError
from satorici.classes.utils import FAIL_COLOR, puts, autoformat

HOST = "https://api.satori-ci.com"


class SatoriAPI:
    def __init__(self, token: str, server: str, cli_args):
        self.__session__ = requests.Session()
        self.__session__.headers.update(
            Authorization=f"Bearer {token}",
        )
        self.timeout = cli_args.timeout
        self.debug = cli_args.debug
        self.json = cli_args.json
        self.__session__.hooks = {
            "response": lambda r, *args, **kwargs: r.raise_for_status()
        }
        self.server = server or HOST

    def request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.server}/{endpoint}"
        if self.debug:
            print("Request URL:", method, url)
        try:
            resp = self.__session__.request(
                method=method, url=url, timeout=self.timeout, **kwargs
            )
            if self.debug:
                print(resp.headers)
            return resp
        except (ConnectionError, ReadTimeout, HTTPError) as e:
            if self.debug:
                res: Response = e.response
                status = res.json()
                if self.json:
                    puts(FAIL_COLOR, str(status))
                else:
                    autoformat(status, capitalize=True, color=FAIL_COLOR)
            else:
                puts(FAIL_COLOR, "Error")
            sys.exit(1)

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
        id = "/" + args.id if args.id != "list" and args.action != "pending" else ""
        action = "/" + args.action if args.action != "get" else ""
        res = self.request("GET", f"repos{action}{id}", params=parameters)
        return res.json()

    def monitor_get(self, action, parameters):
        if action == "get":
            action = ""
        res = self.request("GET", f"monitors/{action}", params=parameters)
        return res.json()

    def monitor_delete(self, parameters):
        res = self.request("DELETE", "monitors", params=parameters)
        return res.ok

    def report_get(self, args, parameters):
        id = "/" + args.id if args.id != "list" else ""
        action = "/" + args.action if args.action != "get" else ""
        res = self.request("GET", f"reports{action}{id}", params=parameters)
        report = res.json()
        if isinstance(report, dict) and report.get("json"):
            for e in report["json"]:
                e.pop("gfx", None)
        return report

    def report_delete(self, parameters) -> None:
        self.request("DELETE", f"reports/{parameters['id']}")

    def dashboard(self):
        res = self.request("GET", "dashboard")
        return res.json()

    def playbook_get(self, parameters):
        res = self.request("GET", "playbooks", params=parameters)
        return res.json()

    def playbook_delete(self, parameters) -> None:
        self.request("DELETE", "playbooks", params=parameters)

    def team_get(self, parameters):
        res = self.request("GET", "teams", params=parameters)
        return res.json()

    def team_post(self, parameters):
        res = self.request("POST", "teams", params=parameters)
        return res.json()

    def team_members_get(self, parameters):
        res = self.request("GET", "teams/members", params=parameters)
        return res.json()

    def team_members_put(self, parameters):
        res = self.request("PUT", "teams/members", params=parameters)
        return res.json()

    def team_repos_get(self, parameters):
        res = self.request("GET", "teams/repos", params=parameters)
        return res.json()

    def team_repos_put(self, parameters):
        res = self.request("PUT", "teams/repos", params=parameters)
        return res.json()
