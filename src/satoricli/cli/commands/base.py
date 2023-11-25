from abc import ABC, abstractmethod
from argparse import ArgumentParser
from typing import Optional

from rich import print


class BaseCommand(ABC):
    subcommands: tuple[type["BaseCommand"]] = ()
    name: str
    options: tuple[ArgumentParser] = ()
    global_options: tuple[ArgumentParser] = ()
    default_subcommand: Optional[type["BaseCommand"]]

    def __init__(
        self,
        parser: Optional[ArgumentParser] = None,
        parent: Optional["BaseCommand"] = None,
    ):
        if not parser:
            parser = ArgumentParser(
                self.name, parents=self.options + self.global_options
            )

        if self.help():
            parser.print_help = lambda: print(self.help())

        self._parser = parser
        self.parent = parent
        default_func = None

        if self.subcommands:
            self._subparsers = parser.add_subparsers()

            for subcommand in self.subcommands:
                subparser = self._subparsers.add_parser(
                    subcommand.name, parents=subcommand.options + self.global_options
                )

                _subcommand = subcommand(subparser, self)

                if subcommand is self.default_subcommand:
                    default_func = _subcommand

        self._parser.set_defaults(func=default_func or self)
        self.register_args(self._parser)

    def help(self) -> str:
        ...

    @abstractmethod
    def register_args(self, parser: ArgumentParser):
        ...

    def __call__(self, **kwargs):
        ...

    def parse_args(self):
        return vars(self._parser.parse_args())

    def run(self, args: dict):
        """Parse cli arguments and run the specified function"""

        return args.pop("func")(**args)
