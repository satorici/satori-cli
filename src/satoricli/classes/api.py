import requests
import sys
from requests import Response
from requests.exceptions import HTTPError
from typing import Union, Any, Optional

from .utils import FAIL_COLOR, puts, autoformat, log
from .models import arguments

HOST = "https://api.satori-ci.com"


class SatoriAPI:
    def __init__(self, token: str, server: Union[str, None], cli_args: arguments):
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

    def request(
        self, method: str, endpoint: str, raise_error: bool = False, **kwargs
    ) -> Response:
        url = f"{self.server}/{endpoint}"
        try:
            resp = self.__session__.request(
                method=method, url=url, timeout=self.timeout, **kwargs
            )
            log.debug(resp.headers)
        except HTTPError as e:
            if raise_error:
                raise e
            # Show reponse messages when server response is not 20x
            res: Response = e.response
            log.debug("Response headers:")
            log.debug(res.headers)
            try:
                status = res.json()
            except Exception:
                status = res.text
            if self.debug:
                autoformat(status, capitalize=True, color=FAIL_COLOR, jsonfmt=self.json)
            else:
                msg = "Error when connecting to Satori servers"
                if isinstance(status, dict) and "detail" in status:
                    msg += f": {status['detail']}"
                puts(FAIL_COLOR, msg)
        except Exception as e:
            puts(FAIL_COLOR, "Error when connecting to Satori servers")
            log.debug(e)
        else:  # response is 20x
            return resp
        sys.exit(1)

    def runs(self, run_type: str, data: dict) -> Any:
        res = self.request("POST", f"runs/{run_type}", json=data)
        return res.json()

    def repos(self, method: str, repo: str, action: str, **kwargs) -> Any:
        res = self.request(method, f"repos/{repo}/{action}", **kwargs)
        return res.json()

    def repos_scan(self, method: str, repo: str, action: str, **kwargs) -> Any:
        res = self.request(method, f"repos/scan/{repo}/{action}", **kwargs)
        return res.json()

    def monitors(self, method: str, monitor_id: str, action: str, **kwargs) -> Any:
        res = self.request(method, f"monitors/{monitor_id}/{action}", **kwargs)
        return res.json()

    def monitor_delete(self, parameters: dict) -> None:
        self.request("DELETE", f"monitors/{parameters['id']}")

    def reports(
        self,
        method: str,
        report_id: str,
        action: str,
        raise_error: bool = False,
        **kwargs,
    ) -> Any:
        res = self.request(
            method, f"reports/{report_id}/{action}", raise_error, **kwargs
        )
        report = res.json()
        if isinstance(report, dict) and report.get("json"):
            for e in report["json"]:
                e.pop("gfx", None)
        return report

    def report_delete(self, parameters: dict) -> None:
        self.request("DELETE", f"reports/{parameters['id']}")

    def dashboard(self):
        res = self.request("GET", "dashboard")
        return res.json()

    def playbook(
        self, method: str, obj_id: str, params: Optional[dict] = None
    ) -> Union[dict, str, None]:
        res = self.request(method, f"playbooks/{obj_id}", params=params)
        if obj_id != "":
            return res.text
        if method != "DELETE":
            return res.json()

    def teams(self, method: str, name: str, action: str, **kwargs) -> Any:
        res = self.request(method, f"teams/{name}/{action}", **kwargs)
        try:
            return res.json()
        except Exception:
            return res.text

    def users(self, method: str, user: str, action: str, **kwargs) -> Any:
        res = self.request(method, f"users/{user}/{action}", **kwargs)
        return res.json()
