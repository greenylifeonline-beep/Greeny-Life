"""Safe entry point for the historical brain.

It intentionally checks the requested mode before importing ``brain.py`` so
destructive or synthetic-data modes remain blocked even if optional legacy
Python dependencies are not installed.
"""

from __future__ import annotations

import sys


BLOCKED_FLAGS = {
    "--build-suppliers",
    "--build-certificates",
    "--build-els",
    "--build-customers",
    "--build-analytics",
    "--build-logistics",
    "--build-finance",
    "--build-inventory",
    "--build-crm",
    "--deep-clean",
    "--consolidate",
    "--self-clean",
    "--dynamic-packaging",
    "--build-packaging-visual",
    "--generate-labels-visual",
}


def main(argv: list[str]) -> int:
    requested = sorted(BLOCKED_FLAGS.intersection(argv))
    if requested:
        print(
            "BLOCKED: historical Brain modes are not allowed to generate business data "
            "or move/delete files in the final runtime: " + ", ".join(requested),
            file=sys.stderr,
        )
        return 2
    print(
        "The historical Brain is not an application runtime entry point. "
        "Use the controlled TypeScript APIs and greenlines_brain evidence gate instead.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
