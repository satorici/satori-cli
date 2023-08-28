import json
import requests
import sys
from requests import Response
from requests.exceptions import HTTPError
from typing import Callable, Union, Any, Optional
from websocket import WebSocketApp
from rich.live import Live

from .utils import autoformat, log, console
from .models import RunArgs, arguments, WebsocketArgs

HOST = "https://api.satori-ci.com"
ERROR_MESSAGE = "An error occurred"


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
                autoformat(status, capitalize=True, jsonfmt=self.json)
            else:
                msg = ERROR_MESSAGE
                if isinstance(status, dict) and "detail" in status:
                    msg += f":[/] {status['detail']}"
                console.print("[error]" + msg)
        except Exception as e:
            console.print("[error]" + ERROR_MESSAGE)
            log.debug(e)
        else:  # response is 20x
            return resp
        sys.exit(1)

    def ws_connect(self, args: WebsocketArgs, on_message: Optional[Callable] = None):
        headers = self.__session__.headers
        log.debug(headers)
        url = self.server
        if url.startswith("https://"):
            url = url.replace("https://", "wss://")
        elif url.startswith("http://"):
            url = url.replace("http://", "ws://")
        log.debug(f"{url = }")
        self.on_message = on_message
        self.live = Live("Loading data...", console=console, auto_refresh=False)
        try:
            ws = WebSocketApp(
                url,
                header=[f"Authorization: Bearer {headers.get('Authorization')}"],
                on_open=self.ws_on_open,
                on_message=self.ws_on_message,
                on_error=self.ws_on_error,
                on_close=self.ws_on_close,
            )
        except Exception as e:
            console.print(e)
            sys.exit(1)
        else:
            self.live.start(True)
            self.ws_args = args
            ws.run_forever()
            if ws.has_errored:
                sys.exit(1)

    def ws_on_open(self, app: WebSocketApp):
        log.debug("Connected")
        app.send(self.ws_args.to_json())

    def ws_on_message(self, app: WebSocketApp, message: str):
        log.debug("message")
        if self.on_message:
            self.on_message(app, message, self.live)
        else:
            try:
                # try to load the message as a json
                stats = json.loads(message)
                # make text readable
                output = autoformat(stats, echo=False)
            except Exception:
                # if fail print plain text
                self.live.update(message)
            else:
                if output:
                    self.live.update(output)
            finally:
                self.live.refresh()

    def ws_on_error(self, app: WebSocketApp, error):
        console.print("[error]Error:[/] " + str(error))
        app.has_errored = True

    def ws_on_close(self, app: WebSocketApp, status_code: int, reason: str):
        log.debug("Disconnected")
        log.debug(f"{status_code = }")
        log.debug(f"{reason = }")
        if status_code != 1000:
            self.ws_on_error(app, reason)

    def runs(self, run_type: str, data: RunArgs) -> Any:
        res = self.request("POST", f"runs/{run_type}", json=data.__dict__)
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

    def get_report_output(self, report_id: str):
        r = self.request("GET", f"outputs/{report_id}")
        content = requests.get(r.json()["url"], stream=True, timeout=300)
        return content.iter_lines()

    def get_report_files(self, report_id: str):
        return self.request("GET", f"reports/{report_id}/files", stream=True)

    def report_delete(self, parameters: dict) -> None:
        self.request("DELETE", f"reports/{parameters['id']}")

    def dashboard(self):
        res = self.request("GET", "dashboard")
        return res.json()

    def playbook(self, method: str, obj_id: str, **kwargs) -> Union[dict, str, None]:
        res = self.request(method, f"playbooks/{obj_id}", **kwargs)
        if obj_id != "":
            return res.text
        if method != "DELETE":
            return res.json()

    def teams(self, method: str, name: str, action: str, **kwargs) -> Any:
        res = self.request(method, f"teams/{name}/{action}", **kwargs)
        if "application/json" in res.headers["content-type"]:
            return res.json()
        else:
            return res.text

    def users(self, method: str, user: str, action: str, **kwargs) -> Any:
        res = self.request(method, f"users/{user}/{action}", **kwargs)
        return res.json()
