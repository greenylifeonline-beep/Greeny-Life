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


from cognitive_event_bus import (
    emit,
    replay_wal,
    load_jsonl,
    WAL_FILE,
    PROCESSED_LEDGER,
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
        prog="raios-a4"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    event = sub.add_parser(
        "emit"
    )

    event.add_argument(
        "event_type"
    )

    event.add_argument(
        "intent"
    )

    event.add_argument(
        "--actor",
        default="RAIOS.CLI",
    )

    event.add_argument(
        "--tool",
        default="RAIOS.A4.CLI",
    )

    event.add_argument(
        "--confidence",
        type=float,
        default=None,
    )

    sub.add_parser(
        "replay"
    )

    sub.add_parser(
        "status"
    )

    args = parser.parse_args()

    if args.command == "emit":

        output(
            emit(
                event_type=
                    args.event_type,

                actor=
                    args.actor,

                intent=
                    args.intent,

                tool=
                    args.tool,

                confidence=
                    args.confidence,
            )
        )

    elif args.command == "replay":

        output(
            replay_wal()
        )

    elif args.command == "status":

        wal = load_jsonl(
            WAL_FILE
        )

        processed = load_jsonl(
            PROCESSED_LEDGER
        )

        output({
            "schema":
                "raios.event-bus-status.v1",

            "wal_events":
                len(wal),

            "processed_records":
                len(processed),

            "unique_wal_events":
                len({
                    item.get(
                        "event_id"
                    )
                    for item in wal
                    if item.get(
                        "event_id"
                    )
                }),

            "unique_processed_events":
                len({
                    item.get(
                        "event_id"
                    )
                    for item in processed
                    if item.get(
                        "event_id"
                    )
                }),
        })


if __name__ == "__main__":
    main()