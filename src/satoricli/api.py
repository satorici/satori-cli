import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from httpx import Client, Response

from satoricli.auth import refresh_access_token

from .exceptions import SatoriError, SatoriRequestError

HOST = "https://api.satori.ci"
WS_HOST = "wss://api.satori.ci"

SATORI_HOME = Path.home() / ".satori"
SATORI_HOME.mkdir(exist_ok=True)


def raise_on_error(res: Response):
    if res.status_code == 401:
        try:
            refresh_token = os.environ["SATORI_REFRESH_TOKEN"]
        except KeyError:
            raise SatoriError("Unable to refresh access token")

        token = refresh_access_token(refresh_token)
        (SATORI_HOME / "access-token").write_text(token)
        client.headers.update({"Authorization": f"Bearer {token}"})

        # Hack to replace response
        res.__dict__ = client.send(res.request).__dict__
        return

    if res.is_error:
        try:
            res.read()
            message = res.json().get("detail", "Unknown error")
        except Exception:
            message = "Unknown error"

        raise SatoriRequestError(message, status_code=res.status_code)


client = Client(
    base_url=os.getenv("SATORI_HOST", HOST),
    follow_redirects=True,
    event_hooks={"response": [raise_on_error]},
    timeout=60,
)


def configure_client(
    token: Optional[str] = None,
    timeout: Optional[int] = None,
    host: Optional[str] = None,
):
    if token:
        final_token = token
    elif (SATORI_HOME / "access-token").is_file():
        final_token = (SATORI_HOME / "access-token").read_text()
    elif refresh_token := os.getenv("SATORI_REFRESH_TOKEN"):
        final_token = refresh_access_token(refresh_token)
        (SATORI_HOME / "access-token").write_text(final_token)
    else:
        raise SatoriError("Missing credentials")

    client.headers.update({"Authorization": f"Bearer {final_token}"})

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
