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

    def get_report_output(self, id):
        res = self.__session__.get(f"{HOST}/report/output/{id}")
        return res.json()

    def get_report_status(self, id):
        res = self.__session__.get(f"{HOST}/report/status/{id}")
        return res.json()

    def start_scan(self, parameters):
        res = self.__session__.get(f"{HOST}/scan/start", params=parameters)
        return res.json()

    def clean_repo_info(self, parameters):
        res = self.__session__.get(f"{HOST}/scan/clean", params=parameters)
        return res.text

    def get_scan_info(self, parameters):
        res = self.__session__.get(f"{HOST}/info", params=parameters)
        return res.json()

    def get_ci_info(self, parameters):
        res = self.__session__.get(f"{HOST}/ci", params=parameters)
        return res.json()

    def get_monitor_info(self, parameters):
        res = self.__session__.get(f"{HOST}/monitor", params=parameters)
        return res.json()

    def get_report_json(self, uuid):
        res = self.__session__.get(f"{HOST}/report/info/{uuid}")
        return res.text

    def get_report_info(self, parameters):
        res = self.__session__.get(f"{HOST}/report/info", params=parameters)
        return res.json()

    def stop_scan(self, parameters):
        res = self.__session__.get(f"{HOST}/stop", params=parameters)
        return res.json()

    def cron(self, action, param):
        res = self.__session__.get(f"{HOST}/cron/{action}/{param}")
        return res.json()

    def dashboard(self):
        res = self.__session__.get(f"{HOST}/dashboard")
        return res.json()
