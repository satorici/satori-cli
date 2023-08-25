from argparse import ArgumentParser
from datetime import date

date_args = ArgumentParser(add_help=False)
date_args.add_argument(
    "--from",
    type=date.fromisoformat,
    help="date in ISO format",
    metavar="DATE",
    dest="from_date",
)
date_args.add_argument(
    "--to",
    type=date.fromisoformat,
    help="date in ISO format",
    metavar="DATE",
    dest="to_date",
)

json_arg = ArgumentParser(add_help=False)
json_arg.add_argument("-j", "--json", action="store_true", help="JSON output")

profile_arg = ArgumentParser(add_help=False)
profile_arg.add_argument("-P", "--profile", default="default")
