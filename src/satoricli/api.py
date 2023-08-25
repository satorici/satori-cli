import requests

HOST = "https://api.satori-ci.com"
WS_HOST = "wss://api.satori-ci.com"

client = requests.Session()


def configure_client(token: str):
    client.headers.update(Authorization=f"Bearer {token}")
    client.hooks = {"response": lambda r, *args, **kwargs: r.raise_for_status()}
