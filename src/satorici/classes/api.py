import requests

HOST = "https://api.satori-ci.com"


class SatoriAPI:
    def __init__(self, token: str):
        self.__session__ = requests.Session()
        self.__session__.headers.update(
            Authorization=f"Bearer {token}",
        )
        self.__session__.hooks = {
            "response": lambda r, *args, **kwargs: r.raise_for_status()
        }

    def debug_bridge(self, res: requests.Response, args) -> dict:
        if args.debug:
            print("Response headers:", res.headers)
        return res.json()

    def get_bundle_presigned_post(self, args):
        res = self.__session__.get(f"{HOST}/run/bundle", data={"secrets": args.data})
        return self.debug_bridge(res, args)

    def get_archive_presigned_post(self, args):
        res = self.__session__.get(f"{HOST}/run/archive", data={"secrets": args.data})
        return self.debug_bridge(res, args)

    def repo_get(self, args, parameters):
        if args.action == "get":
            args.action = ""
        res = self.__session__.get(f"{HOST}/repo/{args.action}", params=parameters)
        return self.debug_bridge(res, args)

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

    def team_get(self, parameters):
        res = self.__session__.get(f"{HOST}/team", params=parameters)
        return res.json()

    def team_post(self, parameters):
        res = self.__session__.post(f"{HOST}/team", params=parameters)
        return res.json()

    def team_members_get(self, parameters):
        res = self.__session__.get(f"{HOST}/team/members", params=parameters)
        return res.json()

    def team_members_put(self, parameters):
        res = self.__session__.put(f"{HOST}/team/members", params=parameters)
        return res.json()

    def team_repos_get(self, parameters):
        res = self.__session__.get(f"{HOST}/team/repos", params=parameters)
        return res.json()

    def team_repos_put(self, parameters):
        res = self.__session__.put(f"{HOST}/team/repos", params=parameters)
        return res.json()
