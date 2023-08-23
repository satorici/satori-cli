from dataclasses import dataclass
import json
from typing import Any, Optional, Union
from argparse import Namespace


@dataclass
class BaseArgs:
    def to_json(self):
        return json.dumps(self.__dict__)


@dataclass
class Args:
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
    files: bool


@dataclass
class WebsocketArgs(BaseArgs):
    action: str
    id: str
    params: Optional[dict] = None


@dataclass
class RunArgs(BaseArgs):
    secrets: str
    is_monitor: Optional[bool] = None
    url: Optional[str] = None


arguments = Union[Namespace, Args]
