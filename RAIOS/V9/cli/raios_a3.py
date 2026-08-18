from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)

V9 = REPO / "RAIOS" / "V9"

sys.path.insert(
    0,
    str(V9 / "runtime"),
)

sys.path.insert(
    0,
    str(
        V9 /
        "cognition" /
        "semantic"
    ),
)

from experience_reflex import instrumented_call
from semantic_engine import (
    understand_artifact,
    compare_artifacts,
    clamp_confidence,
)


def output(obj):
    print(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
        )
    )


def understand_command(path: str):
    return instrumented_call(
        intent=
            "Evidence-native semantic understanding",

        action=
            "SEMANTIC_UNDERSTAND",

        tool=
            "RAIOS.V9.A3",

        input_data={
            "path": path,
        },

        evidence_refs=[
            path,
        ],

        fn=lambda:
            understand_artifact(
                path
            ),
    )


def compare_command(paths: list[str]):
    return instrumented_call(
        intent=
            "Compare evidence-native artifacts",

        action=
            "SEMANTIC_COMPARE",

        tool=
            "RAIOS.V9.A3",

        input_data={
            "paths": paths,
        },

        evidence_refs=paths,

        fn=lambda:
            compare_artifacts(
                paths
            ),
    )


def verify_capability(
    query: str,
    limit: int,
):
    cli = V9 / "cli" / "raios_v9.py"

    history = (
        V9 /
        "runtime" /
        "git_history_search.py"
    )

    current_proc = subprocess.run(
        [
            sys.executable,
            str(cli),
            "search",
            query,
            "--limit",
            str(limit),
        ],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if current_proc.returncode != 0:
        raise RuntimeError(
            "CURRENT_SEARCH_FAILED\n"
            + current_proc.stderr
        )

    current = json.loads(
        current_proc.stdout
    )

    git_proc = subprocess.run(
        [
            sys.executable,
            str(history),
            query,
            "--limit",
            str(limit),
        ],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if git_proc.returncode != 0:
        raise RuntimeError(
            "GIT_HISTORY_SEARCH_FAILED\n"
            + git_proc.stderr
        )

    historical = json.loads(
        git_proc.stdout
    )

    evidence = []

    for item in current.get(
        "matches",
        []
    ):
        evidence.append({
            "source":
                "CURRENT_TREE",

            "path":
                item.get("path"),

            "kind":
                item.get("kind"),

            "authority":
                "CURRENT_OBSERVATION",
        })

    for item in historical.get(
        "matches",
        []
    ):
        evidence.append({
            "source":
                "GIT_HISTORY",

            "path":
                item.get("path"),

            "commit":
                item.get("commit"),

            "mechanism":
                item.get("mechanism"),

            "authority":
                "HISTORICAL_EVIDENCE",
        })

    unresolved = []

    if not evidence:
        unresolved.append(
            "NO_EVIDENCE_FOUND"
        )

    current_count = sum(
        1
        for e in evidence
        if e["source"]
        == "CURRENT_TREE"
    )

    historical_count = sum(
        1
        for e in evidence
        if e["source"]
        == "GIT_HISTORY"
    )

    result = {
        "schema":
            "raios.capability-verification.v1",

        "query":
            query,

        "evidence_count":
            len(evidence),

        "current_tree_evidence":
            current_count,

        "historical_evidence":
            historical_count,

        "evidence":
            evidence,

        "confidence":
            clamp_confidence(
                0.95
                if current_count > 0
                else (
                    0.70
                    if historical_count > 0
                    else 0.0
                )
            ),

        "unresolved_flags":
            unresolved,

        "epistemic_status":
            "EVIDENCE_BOUNDED",

        "canonical_promotion":
            False,

        "decision":
            (
                "SUPPORTED"
                if current_count > 0
                else
                "HISTORICAL_ONLY"
                if historical_count > 0
                else
                "NOT_PROVEN"
            ),
    }

    return result


def verify_command(
    query: str,
    limit: int,
):
    return instrumented_call(
        intent=
            "Verify capability using current and historical evidence",

        action=
            "CAPABILITY_VERIFY",

        tool=
            "RAIOS.V9.A3",

        input_data={
            "query": query,
            "limit": limit,
        },

        fn=lambda:
            verify_capability(
                query,
                limit,
            ),
    )


def confidence_test(value: float):
    return {
        "schema":
            "raios.confidence-contract-test.v1",

        "input":
            value,

        "normalized":
            clamp_confidence(
                value
            ),
    }


def main():
    parser = argparse.ArgumentParser(
        prog="raios-a3"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    understand = sub.add_parser(
        "understand"
    )

    understand.add_argument(
        "path"
    )

    compare = sub.add_parser(
        "compare"
    )

    compare.add_argument(
        "paths",
        nargs="+",
    )

    verify = sub.add_parser(
        "verify-capability"
    )

    verify.add_argument(
        "query"
    )

    verify.add_argument(
        "--limit",
        type=int,
        default=50,
    )

    conf = sub.add_parser(
        "confidence-test"
    )

    conf.add_argument(
        "value",
        type=float,
    )

    args = parser.parse_args()

    if args.command == "understand":
        output(
            understand_command(
                args.path
            )
        )

    elif args.command == "compare":
        output(
            compare_command(
                args.paths
            )
        )

    elif args.command == "verify-capability":
        output(
            verify_command(
                args.query,
                args.limit,
            )
        )

    elif args.command == "confidence-test":
        output(
            confidence_test(
                args.value
            )
        )


if __name__ == "__main__":
    main()