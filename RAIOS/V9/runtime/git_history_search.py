from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
REPO = Path(
    os.getenv("RAIOS_CANONICAL_REPO", str(Path(__file__).resolve().parents[3]))
).expanduser().resolve()


def run_git(args: list[str]) -> str:
    p = subprocess.run(
        ["git", *args],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )

    if p.returncode != 0:
        raise RuntimeError(
            f"GIT_COMMAND_FAILED: git {' '.join(args)}\n{p.stderr}"
        )

    return p.stdout


def historical_paths(query: str, limit: int = 50) -> list[dict]:
    query_lower = query.lower()
    output = run_git([
        "log",
        "--all",
        "--name-only",
        "--pretty=format:%H",
    ])

    current_commit = None
    matches: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for raw in output.splitlines():
        line = raw.strip()

        if not line:
            continue

        if len(line) == 40 and all(c in "0123456789abcdef" for c in line.lower()):
            current_commit = line
            continue

        if query_lower in line.lower():
            key = (current_commit or "", line)

            if key in seen:
                continue

            seen.add(key)

            matches.append({
                "mechanism": "GIT_HISTORICAL_PATH",
                "commit": current_commit,
                "path": line,
            })

            if len(matches) >= limit:
                break

    return matches


def historical_content(query: str, limit: int = 50) -> list[dict]:
    output = run_git([
        "log",
        "--all",
        "-S",
        query,
        "--pretty=format:%H",
        "--name-only",
    ])

    current_commit = None
    matches: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for raw in output.splitlines():
        line = raw.strip()

        if not line:
            continue

        if len(line) == 40 and all(c in "0123456789abcdef" for c in line.lower()):
            current_commit = line
            continue

        key = (current_commit or "", line)

        if key in seen:
            continue

        seen.add(key)

        matches.append({
            "mechanism": "GIT_HISTORICAL_CONTENT",
            "commit": current_commit,
            "path": line,
        })

        if len(matches) >= limit:
            break

    return matches


def search_git_history(query: str, limit: int = 50) -> dict:
    path_hits = historical_paths(query, limit)
    content_hits = historical_content(query, limit)

    merged = []
    seen = set()

    for item in [*path_hits, *content_hits]:
        key = (
            item.get("mechanism"),
            item.get("commit"),
            item.get("path"),
        )

        if key in seen:
            continue

        seen.add(key)
        merged.append(item)

        if len(merged) >= limit:
            break

    counts = {}

    for item in merged:
        m = item["mechanism"]
        counts[m] = counts.get(m, 0) + 1

    return {
        "schema": "raios.git-history-search.v1",
        "query": query,
        "count": len(merged),
        "mechanism_counts": counts,
        "matches": merged,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()

    print(json.dumps(
        search_git_history(args.query, args.limit),
        indent=2,
        ensure_ascii=False,
    ))