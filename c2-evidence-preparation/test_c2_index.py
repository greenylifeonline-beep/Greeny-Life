#!/usr/bin/env python3
"""Validate C2 evidence-preparation outputs. Does not rehash blobs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("/workspace/c2-evidence-preparation")
REQUIRED = [
    "EVIDENCE-REUSE-INDEX.json",
    "EVIDENCE-HASH-GROUPS.json",
    "EVIDENCE-TOPIC-MAP.json",
    "EVIDENCE-CONTRADICTIONS.json",
    "FUTURE-DEEP-ANALYSIS-TARGETS.json",
    "C2-EVIDENCE-PREPARATION-RECEIPT.json",
]
TOPICS = [
    "RAIOS",
    "C5",
    "memory",
    "retrieval/index",
    "NeuroLingua",
    "WAL/events",
    "model registry",
    "Qwen",
    "Granite",
    "DeepSeek",
    "training",
    "continual learning",
    "council",
    "foundry",
    "cloud/nomadic",
    "model lab",
    "self-inspection",
    "consolidation",
    "GL005/auth",
    "runtime",
    "architecture",
]


def fail(msg: str) -> None:
    print("FAIL:", msg)
    sys.exit(1)


def main() -> int:
    docs = {}
    for name in REQUIRED:
        p = OUT / name
        if not p.exists():
            fail(f"missing {name}")
        docs[name] = json.loads(p.read_text())
        print("ok json", name, "bytes", p.stat().st_size)

    receipt = docs["C2-EVIDENCE-PREPARATION-RECEIPT.json"]
    flags = receipt["flags"]
    assert flags["MODE"] == "READ_ONLY"
    assert flags["C3_WORK_DUPLICATED"] is False
    assert flags["SAME_HASH_REANALYZED"] is False
    assert flags["CURRENT_TRUTH_INFERRED_FROM_OLD_REPORTS"] is False
    assert flags["CANONICAL_ROOT_PROVEN"] is False
    assert flags["READY_FOR_CAPABILITY_ARCHAEOLOGY"] is False
    print("ok flags")

    index = docs["EVIDENCE-REUSE-INDEX.json"]
    arts = index["artifacts"]
    ids = [a["id"] for a in arts]
    if len(ids) != len(set(ids)):
        fail("duplicate artifact ids")
    for a in arts:
        for k in ("path", "sha256", "size", "apparent_subject", "temporal_class", "reuse"):
            if k not in a:
                fail(f"{a.get('id')} missing {k}")
        if a["reuse"].get("reusable_now_as_current_runtime_truth") is True:
            fail(f"{a['id']} claimed current runtime truth")
        if a.get("on_current_disk") and a["path"].startswith(".ai-os/"):
            fail("current disk unexpectedly has .ai-os path in index")
    print("ok artifacts", len(arts))

    groups = docs["EVIDENCE-HASH-GROUPS.json"]
    if groups["law"]["SAME_HASH_REANALYZED"] is not False:
        fail("hash groups claim reanalysis")
    seen = set()
    for g in groups["groups"]:
        if g["sha256"] in seen:
            fail("duplicate hash group")
        seen.add(g["sha256"])
        if g.get("same_hash_reanalyzed") is not False:
            fail("group reanalyzed")
    print("ok hash groups", groups["unique_sha256_count"], "dup_groups", groups["duplicate_groups_count"])

    tmap = docs["EVIDENCE-TOPIC-MAP.json"]["topics"]
    for t in TOPICS:
        if t not in tmap:
            fail(f"missing topic {t}")
    print("ok topics", len(tmap))

    contr = docs["EVIDENCE-CONTRADICTIONS.json"]
    if contr["current_truth_inferred_from_old_reports"] is not False:
        fail("contradictions inferred current truth")
    if contr["resolution_policy"] != "DO_NOT_RESOLVE_BY_ASSUMPTION":
        fail("resolution policy")
    if any(c.get("resolution") != "UNRESOLVED" for c in contr["contradictions"]):
        fail("a contradiction was resolved")
    print("ok contradictions", len(contr["contradictions"]))

    targets = docs["FUTURE-DEEP-ANALYSIS-TARGETS.json"]
    if "do_not_duplicate_C3_tree_census" not in targets["explicit_non_actions_still_in_force"]:
        fail("missing C3 non-action")
    if "do_not_execute_brain.py" not in targets["explicit_non_actions_still_in_force"]:
        fail("missing brain.py non-action")
    print("ok future targets", len(targets["targets"]))

    # Cross-tree C3-like files indexed, not expanded
    c3_names = ["CANONICAL-ROOT.json", "CROSS-TREE-MANIFEST.json", "UNIFICATION-RECEIPT.json"]
    indexed_c3 = [a["path"] for a in arts if any(n in a["path"] for n in c3_names)]
    if not indexed_c3:
        fail("prior C3-like reports were not indexed for reuse")
    # Must not include expanded file lists from CROSS-TREE-MANIFEST as new census rows
    if any(a["path"].startswith("/tmp/c5-clone") for a in arts):
        fail("C3 tmp clone paths leaked into index as census")
    print("ok c3-like indexed not expanded", indexed_c3[:6])

    notebook = [a for a in arts if a["path"].endswith("notebook8c2d6a9080.ipynb")]
    if not notebook:
        fail("RAIOS notebook missing from index")
    print("ok notebook indexed")

    health = next((a for a in arts if a["path"] == "health.json"), None)
    if not health:
        fail("health.json missing")
    if health["header_peek"].get("claimed_status") != "SUCCESS":
        fail(f"health.json status peek failed: {health['header_peek']} subject={health['apparent_subject']}")
    print("ok health parse", health["apparent_subject"], health["header_peek"].get("claimed_status"))

    canon = next((a for a in arts if a["path"].endswith("CANONICAL-ROOT.json") and a.get("sha256")), None)
    if not canon:
        fail("CANONICAL-ROOT.json missing")
    if canon["header_peek"].get("claimed_canonical") is True and flags["CANONICAL_ROOT_PROVEN"] is not False:
        fail("inherited canonical claim")
    print("ok canonical-root indexed as claim only", canon["apparent_subject"])

    print("ALL_CHECKS_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
