import requests

HOST = "https://nuvyp2kffa.execute-api.us-east-2.amazonaws.com"


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

    # def get_report_output(self, id):
    #     res = self.__session__.get(f"{HOST}/report/output/{id}")
    #     return res.json()

    # def get_report_status(self, id):
    #     res = self.__session__.get(f"{HOST}/report/status/{id}")
    #     return res.json()

    def repo_get(self, parameters):
        res = self.__session__.get(f"{HOST}/repo", params=parameters)
        return res.json()

    def repo_commits(self, parameters):
        res = self.__session__.get(f"{HOST}/repo/commits", params=parameters)
        return res.json()

    def repo_check_commits(self, parameters):
        res = self.__session__.get(f"{HOST}/repo/check-commits", params=parameters)
        return res.json()

    def repo_check_forks(self, parameters):
        res = self.__session__.get(f"{HOST}/repo/check-forks", params=parameters)
        return res.json()

    def repo_scan(self, parameters):
        res = self.__session__.get(f"{HOST}/repo/scan", params=parameters)
        return res.json()

    def repo_run(self, parameters):
        res = self.__session__.get(f"{HOST}/repo/run", params=parameters)
        return res.json()

    def repo_clean(self, parameters):
        res = self.__session__.get(f"{HOST}/repo/clean", params=parameters)
        return res.json()

    # def clean_repo_info(self, parameters):
    #     res = self.__session__.get(f"{HOST}/scan/clean", params=parameters)
    #     return res.text

    # def get_scan_info(self, parameters):
    #     res = self.__session__.get(f"{HOST}/info", params=parameters)
    #     return res.json()

    # def get_ci_info(self, parameters):
    #     res = self.__session__.get(f"{HOST}/ci", params=parameters)
    #     return res.json()

    # def get_monitor_info(self, parameters):
    #     res = self.__session__.get(f"{HOST}/monitor", params=parameters)
    #     return res.json()

    # def get_report_json(self, uuid):
    #     res = self.__session__.get(f"{HOST}/report/info/{uuid}")
    #     return res.json()

    # def get_report_info(self, parameters):
    #     res = self.__session__.get(f"{HOST}/report/info", params=parameters)
    #     return res.json()

    # def stop_scan(self, parameters):
    #     res = self.__session__.get(f"{HOST}/stop", params=parameters)
    #     return res.json()

    # def cron(self, action, param):
    #     res = self.__session__.get(f"{HOST}/cron/{action}/{param}")
    #     return res.json()

    def dashboard(self):
        res = self.__session__.get(f"{HOST}/dashboard")
        return res.json()

    # def remove_report(self, parameters):
    #     res = self.__session__.delete(f"{HOST}/report", params=parameters)
    #     return res.json()

    # def remove_monitor(self, parameters):
    #     res = self.__session__.delete(f"{HOST}/monitor", params=parameters)
    #     return res.json()

    def playbook_get(self, parameters):
        res = self.__session__.get(f"{HOST}/playbook", params=parameters)
        return res.json()

    def playbook_delete(self, parameters):
        res = self.__session__.delete(f"{HOST}/playbook", params=parameters)
        return res.json()
