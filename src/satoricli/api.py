from contextlib import contextmanager
from typing import Optional

from httpx import Client, Response

from .exceptions import SatoriRequestError

HOST = "https://api.satori.ci"
WS_HOST = "wss://api.satori.ci"


def raise_on_error(res: Response):
    if not res.is_success:
        try:
            res.read()
            message = res.json().get("detail", "Unknown error")
        except Exception:
            message = "Unknown error"

        raise SatoriRequestError(message, status_code=res.status_code)


client = Client(
    base_url=HOST,
    follow_redirects=True,
    event_hooks={"response": [raise_on_error]},
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


@contextmanager
def disable_error_raise():
    try:
        client.event_hooks["response"].remove(raise_on_error)
        yield client
    finally:
        client.event_hooks["response"].append(raise_on_error)
