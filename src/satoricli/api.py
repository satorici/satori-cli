from typing import Optional

import httpx

HOST = "https://api.satori-ci.com"
WS_HOST = "wss://api.satori-ci.com"

client = httpx.Client(
    base_url=HOST,
    follow_redirects=True,
    event_hooks={"response": [lambda r: r.raise_for_status()]},
    timeout=5,
)


def configure_client(
    token: str, timeout: Optional[int] = None, host: Optional[str] = None
):
    client.headers.update({"Authorization": f"Bearer {token}"})

    if host:
        client.base_url = host

    if timeout:
        client.timeout = timeout
