from argparse import ArgumentParser

from satoricli.api import client

from ..utils import console
from .base import BaseCommand


class FeedbackCommand(BaseCommand):
    name = "feedback"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("message", metavar="MESSAGE", help="Message to send")

    def __call__(self, message: str, **kwargs):
        client.post("/users/feedback", json={"feedback": message})
        console.print("Feedback sent successfully")
