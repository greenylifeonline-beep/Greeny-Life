from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from experience_reflex import capture_event

capture_event(
    intent="Recover critical RAIOS V9 CLI after zero-byte corruption",
    action="FORENSIC_PREIMAGE_RESTORE",
    tool="PowerShell+Python+Git",
    input_data={
        "artifact": "RAIOS/V9/cli/raios_v9.py",
        "observed_bytes": 0,
        "observed_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
    output_data={
        "recovered_bytes": 15385,
        "recovered_sha256": "bbd06a1f8567742221c80093cabd83d4c9eb24889fdd503567ed5aa2f9660c54",
        "hash_match": True,
        "runtime_contract_recovered": True,
    },
    expected_result={
        "recovered_bytes": 15385,
        "recovered_sha256": "bbd06a1f8567742221c80093cabd83d4c9eb24889fdd503567ed5aa2f9660c54",
        "hash_match": True,
        "runtime_contract_recovered": True,
    },
    success=True,
    evidence_refs=[
        "RAIOS/V9/cli/raios_v9.py.v9.0-a1.bak",
        "RAIOS/V9/evidence/quarantined-certifications/",
    ],
    lessons=[
        "Critical artifact writes require transactional mutation.",
        "Exit code zero is insufficient without output-contract validation.",
        "Verified preimage recovery should precede reconstruction.",
    ],
)