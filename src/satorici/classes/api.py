import requests

HOST = "https://api.satori-ci.com"


class SatoriAPI:
    def __init__(self, token: str):
        self.__session__ = requests.Session()
        self.__session__.headers.update(
            Authorization=f"token {token}",
        )
        self.__session__.hooks = {
            "response": lambda r, *args, **kwargs: r.raise_for_status()
        }

    def get_bundle_presigned_post(self):
        res = self.__session__.get(f"{HOST}/uploadurl/bundle")
        return res.json()

    def get_archive_presigned_post(self):
        res = self.__session__.get(f"{HOST}/uploadurl/archive")
        return res.json()

    def repo_get(self, action, parameters):
        if action == "get":
            action = ""
        res = self.__session__.get(f"{HOST}/repo/{action}", params=parameters)
        return res.json()

    def monitor_get(self, action, parameters):
        if action == "get":
            action = ""
        res = self.__session__.get(f"{HOST}/monitor/{action}", params=parameters)
        return res.json()

    def monitor_delete(self, parameters):
        res = self.__session__.delete(f"{HOST}/monitor", params=parameters)
        return res.json()

    def report_get(self, action, parameters):
        if action == "get":
            action = ""
        res = self.__session__.get(f"{HOST}/report/{action}", params=parameters)
        return res.json()

    def report_delete(self, parameters):
        res = self.__session__.delete(f"{HOST}/report", params=parameters)
        return res.json()

    def dashboard(self):
        res = self.__session__.get(f"{HOST}/dashboard")
        return res.json()

    def playbook_get(self, parameters):
        res = self.__session__.get(f"{HOST}/playbook", params=parameters)
        return res.json()

    def playbook_delete(self, parameters):
        res = self.__session__.delete(f"{HOST}/playbook", params=parameters)
        return res.json()
