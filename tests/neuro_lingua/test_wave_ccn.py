import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from raios_c5_wave_ccn import ARTIFACTS, LAWS, stamp  # noqa: E402
from raios.neuro_lingua.layers import auto_pipeline  # noqa: E402
from raios.neuro_lingua.ops_compile import CORPUS, TARGET, auto_compile, prove_corpus  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"
V9 = ROOT / "RAIOS" / "V9"
sys.path.insert(0, str(V9))


def test_wave_ccn_fail_closed_no_wal_no_gl005_no_delete():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = stamp()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["from"] == "C2"
    assert rec["c5"] == "git"
    assert rec["wave"] == "RAIOS-CLOUD-CONSOLIDATION-NEUROLINGUA"
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False
    assert before == after
    flags = rec["flags"]
    assert flags["EXTRACTED_QWEN_GRANITE"] is False
    assert flags["SAFE_TO_REMOVE_SOURCE"] is False
    assert flags["GL005_PROVEN"] is False
    assert flags["KAGGLE_A_WORKER_PROVEN"] is False
    assert flags["KAGGLE_B_WORKER_PROVEN"] is False
    assert flags["WORK_STEALING_PROVEN"] is False
    assert flags["WORK_STEALING_LOCAL_SIM_PROVEN"] is True
    assert flags["PERSISTENT_COGNITIVE_STORAGE_PROVEN"] is False
    assert flags["NEUROLINGUA_L1_PROVEN"] is False
    assert flags["NEUROLINGUA_L2_PROVEN"] is False
    assert flags["NEUROLINGUA_L3_PROVEN"] is False
    assert flags["NEUROLINGUA_L4_PROVEN"] is False
    assert flags["NEUROLINGUA_E2E_PROVEN"] is False
    assert flags["NEUROLINGUA_CORPUS_TESTED"] is True
    assert flags["MODEL_LAB_FOUNDATION_PROVEN"] is True
    assert flags["SELF_INSPECTION_PROVEN"] is True
    assert flags["REPOSITORY_CONSOLIDATION_PROVEN"] is False
    names = [row["name"] for row in rec["artifacts"]]
    assert names == list(ARTIFACTS)
    for name in ARTIFACTS:
        path = REPORTS / name
        assert path.is_file(), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("gl005_proven") is False
    retired = json.loads((REPORTS / "RETIRED-ASSETS-RECEIPT.json").read_text(encoding="utf-8"))
    assert retired["retire_count"] == 0
    steal = json.loads((REPORTS / "KAGGLE-WORK-STEALING-PROOF.json").read_text(encoding="utf-8"))
    assert steal["work_stealing_proven"] is False
    assert steal["retry_duplicate"] is True
    hw = json.loads((REPORTS / "KAGGLE-HARDWARE-CAPACITY-MATRIX.json").read_text(encoding="utf-8"))
    assert hw["this_vm_probe"]["hardware_state"] in {"CPU_ONLY", "GPU_PRESENT"}
    if hw["this_vm_probe"]["gpu_count"] == 0:
        assert hw["this_vm_probe"]["hardware_state"] == "CPU_ONLY"
        assert hw["this_vm_probe"]["gpu_capacity"] == "NOT_PROVEN"
    qwen = json.loads((REPORTS / "QWEN-RUNTIME-REALITY.json").read_text(encoding="utf-8"))
    assert qwen["do_not_call_qwen_3_6"] is True
    assert qwen["final_backbone"] is None
    assert qwen["cortex_loaded"] is False
    lab = json.loads((REPORTS / "MODEL-LAB-REALITY.json").read_text(encoding="utf-8"))
    assert lab["winner"] is None
    assert lab["registry"]["hardcoded_qwen_winner"] is False
    merge = json.loads((REPORTS / "MODEL-MERGE-LAB-FOUNDATION.json").read_text(encoding="utf-8"))
    assert merge["merge_executor"]["executed"] is False
    assert merge["installed_blindly"] is False
    e2e = json.loads((REPORTS / "NEUROLINGUA-E2E-PROOF.json").read_text(encoding="utf-8"))
    assert e2e["ok"] is True
    assert e2e["text_similarity_used"] is False
    assert set(e2e["locales"]) == {"ar-EG", "ar-GULF", "en", "nb-NO", "sv-SE", "da-DK"}
    assert "NO_BLIND_DELETE" in LAWS


def test_ops_compile_meaning_equivalence_not_text_similarity():
    proof = prove_corpus()
    assert proof["ok"] is True
    assert proof["text_similarity_used"] is False
    assert proof["wal_written"] is False
    for row in proof["rows"]:
        assert row["canonical"] == TARGET
        assert row["llm_calls"] == 0
        assert row["l3_used"] is False
    wired = auto_pipeline("the shipment is on customs hold", target_locale="nb-NO")
    assert wired["manual_layer_invocation"] is False
    assert wired["canonical"] == TARGET
    assert "tollen" in wired["l4"]["generated"].lower()
    unknown = auto_compile("hello there friend")
    assert unknown["ok"] is False
    assert unknown["l3"]["needed"] is True
    assert unknown["l3"]["used"] is False


def test_nomadic_invariants_and_storage_cas():
    from cloud.nomadic.provider_contract import get_provider
    from cloud.nomadic.work_stealing_scheduler import simulate_pair_failover
    from cloud.storage.content_addressing import object_id
    from cloud.storage.local_backend import disposable_roundtrip

    kaggle = get_provider("kaggle-a")
    assert kaggle.is_c5 is False
    assert kaggle.durable_state is False
    rec = simulate_pair_failover()
    assert rec["work_stealing_local_sim_proven"] is True
    assert rec["work_stealing_proven"] is False
    blob = b"abc"
    assert object_id(blob) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    cas = disposable_roundtrip(ROOT / ".ai-os" / "receipts" / "c5-wave-ccn" / "cas-test")
    assert cas["ok"] is True


def test_merge_executor_refuses_and_probes_exist():
    from evolution.model_lab.merge_executor import execute

    blocked = execute({"id": "exp-1", "strategy": "TIES"})
    assert blocked["executed"] is False
    assert blocked["weights_touched"] is False
    for name in (
        "gym/kaggle/KAGGLE-A-HARDWARE-PROBE.py",
        "gym/kaggle/KAGGLE-B-HARDWARE-PROBE.py",
        "gym/kaggle/KAGGLE-A-HARDWARE-PROBE.ipynb",
        "gym/kaggle/KAGGLE-B-HARDWARE-PROBE.ipynb",
        "RAIOS/V9/cloud/nomadic/lease_manager.py",
        "RAIOS/V9/cloud/storage/hf_backend.py",
        "RAIOS/V9/evolution/model_lab/canary_registry.py",
        "RAIOS/V9/autonomic/self_inspection/engine.py",
    ):
        assert (ROOT / name).is_file(), name
    assert CORPUS
