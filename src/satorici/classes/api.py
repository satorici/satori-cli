import requests

HOST = "https://api.satori-ci.com"


class SatoriAPI:
    def __init__(self, token: str, server: str):
        self.__session__ = requests.Session()
        self.__session__.headers.update(
            Authorization=f"Bearer {token}",
        )
        self.__session__.hooks = {
            "response": lambda r, *args, **kwargs: r.raise_for_status()
        }
        self.server = server or HOST

    def debug_bridge(self, res: requests.Response, args) -> dict:
        if args.debug:
            print("Response headers:", res.headers)
        return res.json()

    def get_bundle_presigned_post(self, args):
        res = self.__session__.get(
            f"{self.server}/run/bundle", data={"secrets": args.data}
        )
        return self.debug_bridge(res, args)

    def get_archive_presigned_post(self, args):
        res = self.__session__.get(
            f"{self.server}/run/archive", data={"secrets": args.data}
        )
        return self.debug_bridge(res, args)

    def repo_get(self, args, parameters):
        if args.action == "get":
            args.action = ""
        res = self.__session__.get(
            f"{self.server}/repo/{args.action}", params=parameters
        )
        return self.debug_bridge(res, args)

    def monitor_get(self, action, parameters):
        if action == "get":
            action = ""
        res = self.__session__.get(f"{self.server}/monitor/{action}", params=parameters)
        return res.json()

    def monitor_delete(self, parameters):
        res = self.__session__.delete(f"{self.server}/monitor", params=parameters)
        return res.json()

    def report_get(self, action, parameters):
        if action == "get":
            action = ""
        res = self.__session__.get(f"{self.server}/report/{action}", params=parameters)
        return res.json()

    def report_delete(self, parameters):
        res = self.__session__.delete(f"{self.server}/report", params=parameters)
        return res.json()

    def dashboard(self):
        res = self.__session__.get(f"{self.server}/dashboard")
        return res.json()

    def playbook_get(self, parameters):
        res = self.__session__.get(f"{self.server}/playbook", params=parameters)
        return res.json()

    def playbook_delete(self, parameters):
        res = self.__session__.delete(f"{self.server}/playbook", params=parameters)
        return res.json()

    def team_get(self, parameters):
        res = self.__session__.get(f"{self.server}/team", params=parameters)
        return res.json()

    def team_post(self, parameters):
        res = self.__session__.post(f"{self.server}/team", params=parameters)
        return res.json()

    def team_members_get(self, parameters):
        res = self.__session__.get(f"{self.server}/team/members", params=parameters)
        return res.json()

    def team_members_put(self, parameters):
        res = self.__session__.put(f"{self.server}/team/members", params=parameters)
        return res.json()

    def team_repos_get(self, parameters):
        res = self.__session__.get(f"{self.server}/team/repos", params=parameters)
        return res.json()

    def team_repos_put(self, parameters):
        res = self.__session__.put(f"{self.server}/team/repos", params=parameters)
        return res.json()
