from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


V9 = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(
        V9 /
        "runtime"
    ),
)

from evolution_brain import (
    process_all,
    status,
)


def output(obj):
    print(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
        )
    )


def main():

    parser = argparse.ArgumentParser(
        prog="raios-a5"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "consume"
    )

    sub.add_parser(
        "status"
    )

    args = parser.parse_args()

    if args.command == "consume":
        output(
            process_all()
        )

    elif args.command == "status":
        output(
            status()
        )


if __name__ == "__main__":
    main()