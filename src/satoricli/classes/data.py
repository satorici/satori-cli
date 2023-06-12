from dataclasses import dataclass
from typing import Any, Union
from argparse import Namespace


@dataclass
class Args:
    profile: str = "default"
    debug: bool = False
    json: bool = False
    timeout: int = 180
    id: str = ""
    action: str = ""
    path: str = ""
    data: Any = None
    sync: bool = False
    playbook: str = ""
    page: int = 1
    public: bool = False
    report: bool = False
    output: bool = False
    web: bool = False
    limit: int = 20
    filter: str = ""


arguments = Union[Namespace, Args]
