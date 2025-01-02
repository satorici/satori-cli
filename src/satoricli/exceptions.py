class SatoriError(Exception):
    pass


class SatoriRequestError(SatoriError):
    def __init__(self, *args: object, status_code: int):
        self.status_code = status_code
        super().__init__(*args)
