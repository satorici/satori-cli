from dataclasses import dataclass
from typing import Any, Union
from argparse import Namespace


@dataclass
class args:
    id: str
    action: str
    profile: str
    debug: bool
    json: bool
    path: str
    data: Any
    sync: bool
    timeout: int
    playbook: str
    page: int
    public: bool
    report: bool
    output: bool
    config_name: str
    config_value: str
    email: str
    clean: bool
    deleted: bool


arguments = Union[Namespace, args]
