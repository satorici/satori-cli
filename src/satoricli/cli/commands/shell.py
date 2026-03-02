import fcntl
import os
import select
import signal
import struct
import sys
import termios
import time
import tty
from argparse import ArgumentParser
from typing import Mapping
from satoricli.api import client as v1_client

import httpx
import paramiko
from rich.progress import Progress

from .base import BaseCommand


def get_terminal_size():
    buf = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, b"\x00" * 8)
    rows, cols = struct.unpack("hh", buf[:4])
    return cols, rows


def interactive_shell(host: str, token: str):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

    tries = 0

    while tries < 3:
        try:
            ssh_client.connect(
                hostname=host,
                username="root",
                password=token,
                look_for_keys=False,
                allow_agent=False,
            )
            break
        except paramiko.SSHException:
            time.sleep(1)
            tries += 1

    if tries >= 3:
        print("Can't connect to host")
        sys.exit(1)

    cols, rows = get_terminal_size()
    channel = ssh_client.invoke_shell(term="xterm-256color", width=cols, height=rows)

    def resize_handler(signum, frame):
        cols, rows = get_terminal_size()
        channel.resize_pty(width=cols, height=rows)

    old_handler = signal.signal(signal.SIGWINCH, resize_handler)
    old_tty = termios.tcgetattr(sys.stdin)

    try:
        tty.setraw(sys.stdin.fileno())
        channel.settimeout(0.0)

        while True:
            r, _, _ = select.select([channel, sys.stdin], [], [])

            if channel in r:
                try:
                    data = channel.recv(1024)

                    if not data:
                        break

                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                except Exception:
                    break

            if sys.stdin in r:
                data = os.read(sys.stdin.fileno(), 1024)
                channel.send(data)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        signal.signal(signal.SIGWINCH, old_handler)
        channel.close()
        ssh_client.close()


def remove_none_values(d: Mapping):
    return {k: v for k, v in d.items() if v is not None}


class ShellCommand(BaseCommand):
    name = "shell"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("--image")
        parser.add_argument("--memory", type=int)
        parser.add_argument("--cpu", type=int)
        parser.add_argument("--region", action="append", default=[])

    def __call__(self, cpu, memory, image, region, **kwargs):
        client = httpx.Client(
            base_url="https://api-v2.satori.ci",
            headers=v1_client.headers,
        )

        container_settings = remove_none_values(
            {"cpu": cpu, "memory": memory, "image": image}
        )

        res = client.post(
            "/ssh_sessions",
            json={
                "regions": list(region),
                "container_settings": container_settings,
            },
        )
        res.raise_for_status()
        id = res.json()["id"]

        with Progress(transient=True) as progress:
            progress.add_task("Waiting for host", total=None)

            while True:
                try:
                    res = client.get(f"/ssh_sessions/{id}")
                    res.raise_for_status()
                    session_data = res.json()
                    break
                except Exception:
                    time.sleep(2)

        interactive_shell(session_data["host"], session_data["token"])
