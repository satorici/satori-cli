import requests
import sys
from requests import Response
from requests.exceptions import ConnectionError, ReadTimeout, HTTPError
from satorici.classes.utils import FAIL_COLOR, puts, autoformat, log
from typing import Union

HOST = "https://api.satori-ci.com"


class SatoriAPI:
    def __init__(self, token: str, server: Union[str, None], cli_args):
        self.__session__ = requests.Session()
        self.__session__.headers.update(
            Authorization=f"Bearer {token}",
        )
        self.timeout = cli_args.timeout
        self.debug = cli_args.debug
        if self.debug:
            log.setLevel("DEBUG")
            log.debug(cli_args)
        self.json = cli_args.json
        self.__session__.hooks = {
            "response": lambda r, *args, **kwargs: r.raise_for_status()
        }
        self.server = server or HOST

    def request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.server}/{endpoint}"
        try:
            resp = self.__session__.request(
                method=method, url=url, timeout=self.timeout, **kwargs
            )
            log.debug(resp.headers)
            return resp
        except (ConnectionError, ReadTimeout, HTTPError) as e:
            if self.debug:
                res: Response = e.response
                try:
                    status = res.json()
                except Exception:
                    status = res.text
                autoformat(status, capitalize=True, color=FAIL_COLOR, jsonfmt=self.json)
            else:
                puts(FAIL_COLOR, "Error")
            sys.exit(1)

    def runs(self, run_type: str, secrets: str):
        res = self.request("POST", f"runs/{run_type}", json={"secrets": secrets})
        return res.json()

    def repos(self, method: str, repo: str, action: str, **kwargs):
        res = self.request(method, f"repos/{repo}/{action}", **kwargs)
        return res.json()

    def repos_scan(self, method: str, repo: str, action: str, **kwargs):
        res = self.request(method, f"repos/scan/{repo}/{action}", **kwargs)
        return res.json()

    def monitors(self, method: str, monitor_id: str, action: str, **kwargs):
        res = self.request(method, f"monitors/{monitor_id}/{action}", **kwargs)
        return res.json()

    def monitor_delete(self, parameters) -> None:
        self.request("DELETE", f"monitors/{parameters['id']}")

    def reports(self, method: str, report_id: str, action: str, **kwargs):
        res = self.request(method, f"reports/{report_id}/{action}", **kwargs)
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

    def teams(self, method: str, name: str, action: str, **kwargs):
        res = self.request(method, f"teams/{name}/{action}", **kwargs)
        return res.json()
