"""D-081 CI identity is COMMIT_AND_CI_PROVEN only when run URL head SHA matches."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / ".ai-os" / "receipts" / "c5-screen" / "D081-CI-COMMIT-IDENTITY.json"
ATTESTED = "85fde1c71a4f4aa9d38c766c573458c82224f6ab"
PRIMARY_RUN = "https://github.com/greenylifeonline-beep/Greeny-Life/actions/runs/32907454840"


def test_d081_fields_are_commit_and_ci_proven_without_secrets():
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    blob = json.dumps(rec)
    assert "token" not in blob.lower()
    assert "secret" not in blob.lower() or rec.get("secrets_present") is False
    assert rec["secrets_present"] is False
    assert rec["D081_FULL_SHA"] == ATTESTED
    assert len(rec["D081_FULL_SHA"]) == 40
    assert rec["D081_BRANCH_OR_REF"] == "cursor/c5-screen-identity-4540"
    assert rec["D081_CI_RUN_URL"] == PRIMARY_RUN
    assert rec["D081_CI_PROVIDER"] == "github-actions"
    assert rec["D081_CHECKED_AT_UTC"] == "2026-08-25T22:43:38Z"
    assert rec["D081_CHECKS_TOTAL"] == 4
    assert rec["D081_CHECKS_PASSED"] == 4
    assert rec["D081_IDENTITY_WITHOUT_PYDANTIC"] == "PASS"
    assert rec["D081_RUN_HEAD_SHA"] == rec["D081_FULL_SHA"]
    assert rec["D081_RUN_URL_MATCHES_SHA"] is True
    assert rec["D081_EVIDENCE_STATUS"] == "COMMIT_AND_CI_PROVEN"
    assert rec["D081_CI_PASS"] is True
    assert rec["EXTERNAL_ATTESTATION"] is False
    assert rec["FALSE_FLAGS_PRESERVED"] is True
    assert len(rec["checks"]) == 4
    for row in rec["checks"]:
        assert row["head_sha"] == ATTESTED
        assert row["conclusion"] == "success"
        assert "/actions/runs/" in row["run_url"]
        assert "/job/" in row["job_url"]
    assert rec["C2_JOIN_PROVEN"] is False
    assert rec["COMMAND_FABRIC_E2E_PROVEN"] is False
    assert rec["CROSS_HOST_ROUND_TRIP_PROVEN"] is False
    assert rec["C5_MAIN_CORTEX_PROVEN"] is False
    assert rec["WAL_WRITTEN"] is False
    assert rec["GL005_PROVEN"] is False
    assert rec["challenge_run"] is False
