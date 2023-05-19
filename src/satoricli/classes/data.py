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


arguments = Union[Namespace, args]
