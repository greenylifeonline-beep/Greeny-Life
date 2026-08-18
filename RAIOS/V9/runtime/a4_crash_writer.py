from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(
        ROOT /
        "runtime"
    ),
)

from cognitive_event_bus import (
    build_event,
    emit_event,
)


parser = argparse.ArgumentParser()

parser.add_argument(
    "--event-id",
    required=True,
)

parser.add_argument(
    "--correlation-id",
    required=True,
)

args = parser.parse_args()


event = build_event(
    event_type="OBSERVATION",

    actor="RAIOS.A4.CRASH.TEST",

    intent=(
        "Prove Cognitive WAL survives "
        "worker death before materialization"
    ),

    event_id=
        args.event_id,

    correlation_id=
        args.correlation_id,

    success=True,

    input_ref={
        "test":
            "CRASH_AFTER_WAL_BEFORE_MATERIALIZATION"
    },

    evidence_refs=[
        "RAIOS/V9/wal/cognitive-events.jsonl"
    ],

    confidence=1.0,
)


emit_event(
    event,
    materialize=False,
)


# Deliberately terminate without graceful cleanup.
# WAL must already be fsync'ed at this point.

os._exit(91)