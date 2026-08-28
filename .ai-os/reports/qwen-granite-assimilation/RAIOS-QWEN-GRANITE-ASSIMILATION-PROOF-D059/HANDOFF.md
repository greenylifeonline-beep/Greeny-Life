# HANDOFF — RAIOS-QWEN-GRANITE-ASSIMILATION-PROOF-D059

Seat: C2-KAGGLE-CONTROL
Authority: C1
Mode: D-059 ASSIMILATION LANE / BINDING DECISION

## Verdict

Historical `origin/cursor/raios-live-assimilation-147d` was not merged or cherry-picked wholesale (not an ancestor of current primary). Old CCEE/Wave/Parallel/LiveAssimilationBridge/Ollama-as-canonical were not resurrected.

Smallest canonical source-independent assimilation seam is on current primary for both Qwen and Granite.

## Flags

QWEN_CAPABILITY_IDS=brain.assimilated.qwen.CODE_REPAIR,SOURCE_AUTHORITY_REASONING,DEBUGGING,REPOSITORY_REASONING,FAIL_CLOSED_CERTIFICATION,SKILL_COMPILATION,ARCHITECTURE_REASONING,TOOL_USE,TEACHER_STUDENT_LEARNING,TEACHER_SELF_INVENTORY
GRANITE_CAPABILITY_IDS=brain.assimilated.granite.KNOWLEDGE_ASSIMILATION,SOURCE_AUTHORITY_REASONING,DEBUGGING,REPOSITORY_REASONING,FAIL_CLOSED_CERTIFICATION,SKILL_COMPILATION,ARCHITECTURE_REASONING,TOOL_USE,TEACHER_STUDENT_LEARNING,TEACHER_SELF_INVENTORY
QWEN_SOURCE_PROVENANCE=sha256:1caa640079eb71bef9c2719ab17cce75fc6d2a4d5a9f0dbe486332fb520c8397;teacher=qwen2.5-coder:3b;teacher_id=TEACHER_QWEN25_CODER_3B;family=qwen
GRANITE_SOURCE_PROVENANCE=sha256:19dc09a1109fc0c758d29b5f6230ddf1448610a7756e39688ef2a1343af3e33e;teacher=granite4:3b;teacher_id=TEACHER_GRANITE4_3B;family=granite
QWEN_SOURCE_INDEPENDENT=true
GRANITE_SOURCE_INDEPENDENT=true
QWEN_BRAIN_WIRING_PROVEN=true
GRANITE_BRAIN_WIRING_PROVEN=true
QWEN_RUNTIME_PROVEN=true
GRANITE_RUNTIME_PROVEN=true
EXTRACTED_QWEN_GRANITE=intelligence/knowledge_base/assimilated
SAFE_TO_REMOVE_SOURCE=true
D059_ASSIMILATION_SEGMENT_PROVEN=true
GL005_PROVEN=
D059_FULL_CLOSED=false

## Seam

- Runtime: `assimilated_brain.py` (no `_raios*` import, no Ollama)
- Wiring: `brain.py` `inspect_canonical_runtime_health` extra key `assimilated` without changing `capabilities_checked=7`
- Records: `intelligence/knowledge_base/assimilated/{QWEN,GRANITE,INDEX,CAPABILITIES,D059-ACCEPTANCE}.json`
- Gate: `tests/assimilation_acceptance` accepts `D059-ACCEPTANCE.json`

## Tests

- focused 14/14 PASS
- D-059 acceptance gate 10/10 PASS
- resource_fabric 172/172 PASS
- test_c5_canonical_growth: 2 PASS / 3 FAIL, sparse-worktree environment (missing V9 WAL file + third-party `a2a`); not caused by this seam

## Safety

PAID_RESOURCE_CREATED=false
GPU_SESSION_STARTED=false
MODEL_WEIGHTS_STORED=false
HISTORICAL_RUNTIME_IMPORTED=false
HISTORICAL_LINEAGE_147D_MERGED=false

## Next

Do not close full D-059 or set GL005_PROVEN from this segment. Historical harvest trees may be removed from Repair; compiled KB is canonical.
