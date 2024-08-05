from httpx import Client

CLIENT_ID = "Nf8oTFFRFzUY2BWXlyayvUgmMbf6UEAh"
DOMAIN = "https://satorici.us.auth0.com"
AUDIENCE = "https://api.satori.ci"

client = Client(
    base_url=DOMAIN,
    headers={
        "Content-Type": "application/x-www-form-urlencoded",
    },
)


def refresh_access_token(refresh_token: str):
    res = client.post(
        "/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )

    return res.json()["access_token"]
