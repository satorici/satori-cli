import sys
from typing import Optional

import httpx
from rich.console import Console

HOST = "https://api.satori-ci.com"
WS_HOST = "wss://api.satori-ci.com"


def error_handler(r: httpx.Response):
    if r.is_error:
        console = Console()
        try:
            r.read()
            error_data: dict = r.json()
        except Exception:
            console.print("[b]An unknown error ocurred")
        else:
            console.print(
                "[b]An error ocurred:[/] " + error_data.get("detail", "Unknown error")
            )
        console.print("[b]Status code:[/] " + str(r.status_code))
        sys.exit(1)


client = httpx.Client(
    base_url=HOST,
    follow_redirects=True,
    event_hooks={"response": [error_handler]},
    timeout=60,
)


def configure_client(
    token: str, timeout: Optional[int] = None, host: Optional[str] = None
):
    client.headers.update({"Authorization": f"Bearer {token}"})

    if host:
        client.base_url = host

    if timeout:
        client.timeout = timeout
