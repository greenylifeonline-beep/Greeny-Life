"""Live account overlay for the existing Resource Fabric. Not a second registry or census engine."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cost import estimate
from .observations import observation
from .placement import MODEL_WEIGHTS_LOCAL, recompose_v2
from .schema import UNKNOWN, UNOBSERVED, credit, price, quota, utc
from .secrets import assert_no_secrets, mask_record

HOME = Path.home()
C1_KAGGLE_DIR = HOME / ".kaggle"
WAVE06_PACKAGE = (
    Path(__file__).resolve().parents[3]
    / ".ai-os"
    / "reports"
    / "resource-fabric"
    / "RAIOS-RESOURCE-FACTORY-LIVE-BINDING-EXPANSION-WAVE-06"
)
TARGET_ACCOUNTS = (
    "ORACLE_01",
    "KAGGLE_C1",
    "KAGGLE_PARTNER",
    "LIGHTNING_01",
    "COLAB_01",
    "MODAL_01",
    "LOCAL_AG",
)
QWEN_ID = "qwen3.6:35b-a3b"
QWEN_GB = 23.0
MODAL_CATALOG_GPU_SEC = {
    "T4": 0.000164,
    "L4": 0.000222,
    "A10": 0.000306,
    "A100-80GB": 0.000694,
}
MODAL_VOLUME_GIB_MONTH = 0.09
WAVE02_PACKAGE = Path(__file__).resolve().parents[3] / ".ai-os" / "reports" / "resource-fabric" / "RAIOS-RESOURCE-FABRIC-LIVE-ACCOUNT-BINDING-WAVE-02"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_on(name: str) -> bool:
    val = os.environ.get(name)
    return bool(val) and len(str(val)) > 0


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _is_c1_kaggle_dir(path: Path) -> bool:
    try:
        return path.resolve() == C1_KAGGLE_DIR.resolve()
    except OSError:
        return False


def _sha256_file(path: Path) -> Any:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _partner_env_dir() -> Path | None:
    for name in ("KAGGLE_CONFIG_DIR_B", "KAGGLE_PARTNER_CONFIG"):
        raw = os.environ.get(name)
        if not raw:
            continue
        p = Path(raw)
        if p.is_file():
            p = p.parent
        if _is_c1_kaggle_dir(p):
            continue
        return p
    raw = os.environ.get("KAGGLE_CONFIG_B")
    if not raw:
        return None
    p = Path(raw)
    if p.is_file():
        p = p.parent
    if _is_c1_kaggle_dir(p):
        return None
    return p


def _partner_candidate_dirs() -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    temp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or (HOME / "AppData" / "Local" / "Temp"))
    candidates: list[Path] = []
    envd = _partner_env_dir()
    if envd is not None:
        candidates.append(envd)
    candidates.extend((HOME / ".kaggle-partner", HOME / ".kaggle_b", temp / ".kaggle"))
    for p in candidates:
        if _is_c1_kaggle_dir(p):
            continue
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _chrome_kaggle_profile_hint() -> Path:
    return (
        HOME
        / "AppData"
        / "Local"
        / "Google"
        / "Chrome"
        / "User Data"
        / "Profile 5"
        / "IndexedDB"
        / "https_www.kaggle.com_0.indexeddb.leveldb"
    )


def _tcp(host: str, port: int, timeout: float = 2.0) -> str:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return "SUCCESS"
    except OSError:
        return "OFFLINE"
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _run_cli(args: list[str], *, timeout: float = 25.0, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False, env=env)
        out = proc.stdout or ""
        err = proc.stderr or ""
        if any(x in (out + err).lower() for x in ("access_token", "token_secret", "api_key", "bearer ")):
            out, err = "[REDACTED]", "[REDACTED]"
        return {"ok": proc.returncode == 0, "code": proc.returncode, "stdout": out[-8000:], "stderr": err[-2000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": None, "status": "UNAVAILABLE", "reason": "TIMEOUT"}
    except FileNotFoundError:
        return {"ok": False, "code": None, "status": "UNAVAILABLE", "reason": "CLI_ABSENT"}
    except Exception as exc:
        return {"ok": False, "code": None, "status": "UNAVAILABLE", "reason": type(exc).__name__}


def _hours(text: str) -> Any:
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(text))
    if not m:
        return UNKNOWN
    return float(m.group(1))


def _http_json(url: str, headers: dict[str, str], timeout: float = 15.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(500000)
            if raw[:1] not in (b"{", b"["):
                return {"http": resp.status, "json": None}
            return {"http": resp.status, "json": json.loads(raw.decode("utf-8", errors="replace"))}
    except urllib.error.HTTPError as exc:
        return {"http": exc.code, "json": None}
    except Exception as exc:
        return {"http": None, "json": None, "error": type(exc).__name__}


def count_unknown_fields(world: dict[str, Any]) -> dict[str, int]:
    storage_fields = ("capacity_total_gb", "capacity_used_gb", "capacity_free_gb", "quota_gb")
    storage_u = sum(1 for s in world.get("storage") or [] for f in storage_fields if s.get(f) in (None, "", UNKNOWN))
    quota_fields = ("limit", "used", "remaining", "reset_at")
    quota_u = sum(1 for q in world.get("quotas") or [] for f in quota_fields if q.get(f) in (None, "", UNKNOWN))
    credit_fields = ("remaining_value", "original_value", "expires_at")
    credit_u = sum(1 for c in world.get("credits") or [] for f in credit_fields if c.get(f) in (None, "", UNKNOWN))
    price_u = sum(1 for p in world.get("pricing") or [] if p.get("amount") in (None, "", UNKNOWN))
    auth_req = sum(1 for a in world.get("accounts") or [] if a.get("account_id") in TARGET_ACCOUNTS and a.get("status") == "AUTH_REQUIRED")
    return {
        "UNKNOWN_STORAGE_FIELDS": storage_u,
        "AUTH_REQUIRED": auth_req,
        "UNKNOWN_QUOTAS": quota_u,
        "UNKNOWN_CREDITS": credit_u,
        "UNKNOWN_PRICING": price_u,
    }


def discover_auth() -> list[dict[str, Any]]:
    kaggle_oauth = HOME / ".kaggle" / "credentials.json"
    kaggle_legacy = HOME / ".kaggle" / "kaggle.json"
    oci_cfg = HOME / ".oci" / "config"
    lightning_cred = HOME / ".lightning" / "credentials.json"
    modal_toml = HOME / ".modal.toml"
    gcloud = HOME / "AppData" / "Roaming" / "gcloud" / "application_default_credentials.json"
    rows = [
        {
            "account_id": "KAGGLE_C1",
            "provider": "KAGGLE",
            "credential_ref": "existing-session:kaggle-cli-oauth" if _exists(kaggle_oauth) else ("file-ref:%USERPROFILE%/.kaggle/kaggle.json" if _exists(kaggle_legacy) else "existing-receipt:KAGGLE-AUTHENTICATED-READ-RECEIPT"),
            "auth_method": "KAGGLE_CLI_OAUTH" if _exists(kaggle_oauth) else ("KAGGLE_JSON" if _exists(kaggle_legacy) else "UNOBSERVED"),
            "session_state": "CREDENTIAL_FILE_PRESENT" if _exists(kaggle_oauth) or _exists(kaggle_legacy) else "FILE_ABSENT_NOT_PROOF_OF_NO_AUTH",
            "kaggle_json_present": _exists(kaggle_legacy),
            "kaggle_oauth_credentials_present": _exists(kaggle_oauth),
            "cli_present": bool(shutil.which("kaggle")),
            "KAGGLE_JSON_ABSENT_NE_ACCOUNT_ABSENT": True,
        },
        {
            "account_id": "KAGGLE_PARTNER",
            "provider": "KAGGLE",
            "credential_ref": "env:KAGGLE_CONFIG_DIR_B",
            "auth_method": "ISOLATED_KAGGLE_PROFILE",
            "session_state": (
                "CREDENTIAL_FILE_PRESENT"
                if any(
                    (d / name).is_file()
                    for d in _partner_candidate_dirs()
                    for name in ("credentials.json", "kaggle.json")
                )
                else (
                    "SEPARATE_PROFILE_CANDIDATE_PRESENT"
                    if any(d.is_dir() for d in _partner_candidate_dirs()) or _chrome_kaggle_profile_hint().exists()
                    else "AUTH_REQUIRED"
                )
            ),
            "isolated_from": "KAGGLE_C1",
            "copied_from_c1": False,
            "C1_KAGGLE_DIR_REFUSED": True,
        },
        {
            "account_id": "ORACLE_01",
            "provider": "ORACLE_CLOUD",
            "credential_ref": "cli-profile:oci",
            "auth_method": "OCI_CLI_PROFILE",
            "session_state": "CONFIG_PRESENT" if _exists(oci_cfg) else "AUTH_REQUIRED",
            "cli_present": bool(shutil.which("oci")),
        },
        {
            "account_id": "LIGHTNING_01",
            "provider": "LIGHTNING",
            "credential_ref": "file-ref:%USERPROFILE%/.lightning/credentials.json",
            "auth_method": "LIGHTNING_API_BASIC",
            "session_state": "CREDENTIAL_FILE_PRESENT" if _exists(lightning_cred) else "AUTH_REQUIRED",
            "cli_present": bool(shutil.which("lightning")),
        },
        {
            "account_id": "MODAL_01",
            "provider": "MODAL",
            "credential_ref": "file-ref:%USERPROFILE%/.modal.toml",
            "auth_method": "MODAL_TOML_TOKEN",
            "session_state": "CREDENTIAL_FILE_PRESENT" if _exists(modal_toml) else "AUTH_REQUIRED",
            "cli_present": bool(shutil.which("modal")),
        },
        {
            "account_id": "COLAB_01",
            "provider": "COLAB",
            "credential_ref": "env:COLAB_SESSION_REF",
            "auth_method": "GOOGLE_SESSION",
            "session_state": "AUTH_REQUIRED" if not (_env_on("COLAB_SESSION_REF") or _exists(gcloud)) else "CREDENTIAL_PRESENT",
        },
        {
            "account_id": "LOCAL_AG",
            "provider": "GENERIC_HTTP_INFERENCE",
            "credential_ref": "existing:OWNER_LOCAL_CONTROL_PLANE",
            "auth_method": "LOCAL",
            "session_state": "LOCAL",
        },
    ]
    for row in rows:
        row["last_verified"] = UNKNOWN
        assert_no_secrets(row)
    return rows


def _probe_kaggle_c1() -> dict[str, Any]:
    rec: dict[str, Any] = {"account_id": "KAGGLE_C1", "status": "AUTH_REQUIRED"}
    if not shutil.which("kaggle"):
        if _exists(HOME / ".kaggle" / "credentials.json"):
            rec["status"] = "PARTIAL"
            rec["reason"] = "OAUTH_FILE_PRESENT_CLI_PROBE_SKIPPED_OR_ABSENT"
        return rec
    cfg = _run_cli(["kaggle", "config", "view"], timeout=20)
    quota_out = _run_cli(["kaggle", "quota", "--format", "json"], timeout=25)
    if not quota_out.get("ok"):
        quota_out = _run_cli(["kaggle", "quota"], timeout=25)
    ds = _run_cli(["kaggle", "datasets", "list", "--mine", "-p", "1", "--csv"], timeout=30)
    ks = _run_cli(["kaggle", "kernels", "list", "--mine", "-p", "1", "--csv"], timeout=30)
    st = _run_cli(["kaggle", "kernels", "status", "greenylife/raios-canonical-workbench"], timeout=25)
    rec["auth_method"] = "KAGGLE_CLI_OAUTH"
    rec["config_ok"] = bool(cfg.get("ok"))
    rec["username_bound"] = "greenylife" if cfg.get("ok") and "greenylife" in (cfg.get("stdout") or "") else UNKNOWN
    gpu = {"used": UNKNOWN, "remaining": UNKNOWN, "limit": UNKNOWN, "reset_at": UNKNOWN}
    tpu = {"used": UNKNOWN, "remaining": UNKNOWN, "limit": UNKNOWN, "reset_at": UNKNOWN}
    raw_q = quota_out.get("stdout") or ""
    try:
        parsed = json.loads(raw_q) if raw_q.strip().startswith("{") or raw_q.strip().startswith("[") else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        for item in parsed:
            name = str(item.get("resource") or item.get("name") or "").upper()
            target = gpu if "GPU" in name else tpu if "TPU" in name else None
            if target is None:
                continue
            target["used"] = _hours(item.get("used"))
            target["remaining"] = _hours(item.get("remaining"))
            target["limit"] = _hours(item.get("total") or item.get("limit"))
            target["reset_at"] = item.get("refreshAt") or item.get("reset_at") or UNKNOWN
    else:
        for line in raw_q.splitlines():
            if line.strip().upper().startswith("GPU"):
                parts = line.split()
                if len(parts) >= 5:
                    gpu = {"used": _hours(parts[1]), "remaining": _hours(parts[2]), "limit": _hours(parts[3]), "reset_at": parts[4]}
            if line.strip().upper().startswith("TPU"):
                parts = line.split()
                if len(parts) >= 5:
                    tpu = {"used": _hours(parts[1]), "remaining": _hours(parts[2]), "limit": _hours(parts[3]), "reset_at": parts[4]}
    used_bytes = 0
    ds_count = 0
    if ds.get("ok") and "ref," in (ds.get("stdout") or ""):
        reader = csv.DictReader(io.StringIO(ds.get("stdout") or ""))
        for row in reader:
            ds_count += 1
            try:
                used_bytes += int(float(row.get("size") or 0))
            except (TypeError, ValueError):
                pass
    kernel_count = 0
    if ks.get("ok") and "ref," in (ks.get("stdout") or ""):
        kernel_count = max(0, len((ks.get("stdout") or "").strip().splitlines()) - 1)
    active = False
    if st.get("ok"):
        txt = (st.get("stdout") or "").upper()
        active = any(x in txt for x in ("RUNNING", "QUEUED", "STARTING"))
        rec["kernel_status_observed"] = "COMPLETE" if "COMPLETE" in txt else ("RUNNING" if active else UNKNOWN)
    rec.update(
        {
            "status": "REACHABLE" if quota_out.get("ok") or cfg.get("ok") else "PARTIAL",
            "gpu_quota": gpu,
            "tpu_quota": tpu,
            "dataset_count": ds_count,
            "dataset_used_bytes": used_bytes,
            "kernel_count": kernel_count,
            "active_session_gpu": active,
            "account_eligible_gpu": gpu.get("remaining") not in (UNKNOWN, None) and float(gpu.get("remaining") or 0) > 0,
            "current_allocatable_gpu": UNKNOWN,
            "accelerator_types": [n for n, q in (("GPU", gpu), ("TPU", tpu)) if q.get("limit") not in (UNKNOWN, None, "")],
            "gpu_sku": UNOBSERVED,
            "gpu_vram": UNOBSERVED,
            "IDENTITY_PROOF": rec.get("username_bound") or UNOBSERVED,
            "AUTH_RESULT": "REACHABLE" if quota_out.get("ok") or cfg.get("ok") else "PARTIAL",
            "QUOTA_RESULT": {"gpu": gpu, "tpu": tpu, "dataset_count": ds_count, "dataset_used_bytes": used_bytes},
            "REDACTED": True,
            "paid": False,
        }
    )
    return rec


def _probe_lightning() -> dict[str, Any]:
    path = HOME / ".lightning" / "credentials.json"
    rec: dict[str, Any] = {"account_id": "LIGHTNING_01", "status": "AUTH_REQUIRED"}
    if not path.is_file():
        return rec
    try:
        cred = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        rec["status"] = "PARTIAL"
        rec["reason"] = "CREDENTIAL_FILE_UNREADABLE"
        return rec
    uid = cred.get("user_id") or ""
    key = cred.get("api_key") or ""
    if not uid or not key:
        rec["status"] = "PARTIAL"
        rec["reason"] = "CREDENTIAL_FIELDS_MISSING"
        return rec
    import base64

    basic = base64.b64encode(f"{uid}:{key}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}", "Accept": "application/json", "User-Agent": "RAIOS-ResourceFabric/wave02"}
    orgs = _http_json("https://lightning.ai/v1/orgs", headers)
    org_name = UNKNOWN
    org_id = UNKNOWN
    if orgs.get("json") and (orgs["json"].get("organizations") or []):
        org = orgs["json"]["organizations"][0]
        org_name = org.get("name") or UNKNOWN
        org_id = org.get("id") or UNKNOWN
        rec["storage_overuse_bytes"] = org.get("storageOveruseBytes", UNKNOWN)
        rec["allow_credits_auto_replenish"] = org.get("allowCreditsAutoReplenish")
    mem = _http_json("https://lightning.ai/v1/memberships", headers)
    balance = UNKNOWN
    used_bytes = UNKNOWN
    free_store = UNKNOWN
    project_id = UNKNOWN
    jobs = 0
    deployments = 0
    studios = 0
    if mem.get("json") and (mem["json"].get("memberships") or []):
        m0 = mem["json"]["memberships"][0]
        balance = m0.get("balance", UNKNOWN)
        used_bytes = m0.get("currentStorageBytes", UNKNOWN)
        q = m0.get("quotas") or {}
        free_store = q.get("freeStorageBytes", UNKNOWN)
        project_id = m0.get("projectId", UNKNOWN)
        rec["job_count"] = m0.get("jobCount", UNKNOWN)
        rec["datastore_count"] = m0.get("datastoreCount", UNKNOWN)
    if project_id not in (UNKNOWN, None, ""):
        cs = _http_json(f"https://lightning.ai/v1/projects/{project_id}/cloudspaces", headers)
        studios = len((cs.get("json") or {}).get("cloudspaces") or [])
        rec["studio_states"] = [c.get("state") for c in ((cs.get("json") or {}).get("cloudspaces") or [])][:8]
        jobs_j = _http_json(f"https://lightning.ai/v1/projects/{project_id}/jobs", headers)
        jobs = len((jobs_j.get("json") or {}).get("jobs") or [])
        dep_j = _http_json(f"https://lightning.ai/v1/projects/{project_id}/deployments", headers)
        deployments = len((dep_j.get("json") or {}).get("deployments") or [])
    rec.update(
        {
            "status": "REACHABLE" if orgs.get("http") == 200 else "PARTIAL",
            "org_alias": org_name,
            "org_id_present": org_id not in (UNKNOWN, None, ""),
            "credits_remaining": balance,
            "storage_used_bytes": used_bytes,
            "free_storage_bytes": free_store,
            "studio_count": studios,
            "jobs": jobs,
            "deployments": deployments,
            "gpu_model": UNOBSERVED,
            "gpu_sku": UNOBSERVED,
            "gpu_vram": UNOBSERVED,
            "current_allocatable_gpu": UNOBSERVED,
            "account_eligible_gpu": False,
            "IDENTITY_PROOF": org_name if org_name not in (UNKNOWN, None, "") else UNOBSERVED,
            "AUTH_RESULT": "REACHABLE" if orgs.get("http") == 200 else "PARTIAL",
            "QUOTA_RESULT": {
                "credits_remaining": balance,
                "storage_used_bytes": used_bytes,
                "free_storage_bytes": free_store,
                "studio_count": studios,
            },
            "REDACTED": True,
            "paid": False,
        }
    )
    return rec


def _probe_modal_presence() -> dict[str, Any]:
    path = HOME / ".modal.toml"
    rec = {"account_id": "MODAL_01", "status": "AUTH_REQUIRED", "profile": UNKNOWN}
    if not path.is_file():
        return rec
    try:
        import configparser

        cp = configparser.ConfigParser()
        cp.read(path, encoding="utf-8")
        sections = list(cp.sections())
        rec["profile"] = sections[0] if sections else UNKNOWN
        rec["token_fields_present"] = bool(sections) and bool(cp.get(sections[0], "token_id", fallback="")) and bool(
            cp.get(sections[0], "token_secret", fallback="")
        )
        rec["status"] = "REACHABLE_CREDENTIAL_PRESENT" if rec["token_fields_present"] else "PARTIAL"
        rec["reason"] = "TOKEN_FILE_PRESENT_SDK_NOT_USED"
        rec["gpu_catalog"] = list(MODAL_CATALOG_GPU_SEC)
        rec["gpu_entitlement"] = UNOBSERVED
        rec["gpu_sku"] = UNOBSERVED
        rec["gpu_vram"] = UNOBSERVED
        rec["IDENTITY_PROOF"] = f"profile:{rec['profile']}" if rec.get("profile") not in (UNKNOWN, None, "") else UNOBSERVED
        rec["AUTH_RESULT"] = rec["status"]
        rec["QUOTA_RESULT"] = {}
        rec["REDACTED"] = True
        rec["paid"] = False
    except Exception as exc:
        rec["status"] = "PARTIAL"
        rec["reason"] = type(exc).__name__
    return rec


def _probe_kaggle_partner(*, live: bool = True) -> dict[str, Any]:
    """Never uses %USERPROFILE%\\.kaggle. Does not copy or merge C1 credentials."""
    rec: dict[str, Any] = {
        "account_id": "KAGGLE_PARTNER",
        "status": "AUTH_REQUIRED",
        "isolated_from": "KAGGLE_C1",
        "copied_from_c1": False,
        "distinct_from_c1": False,
        "live_auth_proven": False,
        "browser_profile_is_not_cli_credential": True,
        "C1_KAGGLE_DIR_REFUSED": True,
        "IDENTITY_PROOF": UNOBSERVED,
        "AUTH_RESULT": "AUTH_REQUIRED",
        "QUOTA_RESULT": {},
        "REDACTED": True,
        "PROFILE_LABEL": "KAGGLE_PARTNER",
        "gpu_sku": UNOBSERVED,
        "gpu_vram": UNOBSERVED,
        "account_eligible_gpu": False,
    }
    chrome = _chrome_kaggle_profile_hint()
    rec["browser_profile_hint_present"] = chrome.exists()
    dirs = _partner_candidate_dirs()
    rec["candidate_dir_present"] = any(d.is_dir() for d in dirs)
    cred_files = [d / name for d in dirs for name in ("credentials.json", "kaggle.json") if (d / name).is_file()]
    c1_cred = C1_KAGGLE_DIR / "credentials.json"
    c1_legacy = C1_KAGGLE_DIR / "kaggle.json"
    c1_hashes = {h for h in (_sha256_file(c1_cred), _sha256_file(c1_legacy)) if h}
    partner_hashes = []
    for f in cred_files:
        digest = _sha256_file(f)
        if digest:
            partner_hashes.append(digest)
            if digest in c1_hashes:
                rec["copied_from_c1"] = True
    rec["credential_file_present"] = bool(cred_files)
    if rec["copied_from_c1"]:
        rec["status"] = "NOT_DISTINCT_FROM_C1"
        rec["AUTH_RESULT"] = rec["status"]
        rec["distinct_from_c1"] = False
        rec["live_auth_proven"] = False
        return rec
    if rec["credential_file_present"] and live:
        target = cred_files[0].parent
        if _is_c1_kaggle_dir(target):
            rec["status"] = "AUTH_REQUIRED"
            rec["AUTH_RESULT"] = rec["status"]
            rec["reason"] = "REFUSED_C1_KAGGLE_DIR"
            return rec
        env = os.environ.copy()
        isolated_home = target / ".isolated-home"
        isolated_home.mkdir(parents=True, exist_ok=True)
        for key in (
            "KAGGLE_CONFIG_DIR",
            "KAGGLE_API_TOKEN",
            "KAGGLE_API_V1_TOKEN_PATH",
            "KAGGLE_USERNAME",
            "KAGGLE_KEY",
        ):
            env.pop(key, None)
        env["KAGGLE_CONFIG_DIR"] = str(target)
        # Kaggle SDK OAuth credentials live under ~/.kaggle independently of
        # KAGGLE_CONFIG_DIR. Isolate the subprocess home so C1 OAuth can never
        # satisfy or contaminate the partner-account probe.
        env["HOME"] = str(isolated_home)
        env["USERPROFILE"] = str(isolated_home)
        if os.name == "nt":
            env["HOMEDRIVE"] = isolated_home.drive
            env["HOMEPATH"] = str(isolated_home)[len(isolated_home.drive) :]
        cfg = _run_cli(["kaggle", "config", "view"], timeout=20, env=env)
        quota_out = _run_cli(["kaggle", "quota", "--format", "json"], timeout=25, env=env)
        if not quota_out.get("ok"):
            quota_out = _run_cli(["kaggle", "quota"], timeout=25, env=env)
        identity = UNOBSERVED
        stdout = cfg.get("stdout") or ""
        if cfg.get("ok"):
            m = re.search(r"(?im)^\s*-?\s*username\s*[:=]\s*(\S+)", stdout)
            if m:
                identity = m.group(1)
            elif "greenylife" in stdout and stdout.strip():
                identity = "greenylife"
        rec["IDENTITY_PROOF"] = identity
        c1_identity = "greenylife"
        if identity not in (UNOBSERVED, UNKNOWN, None, "") and identity != c1_identity:
            rec["distinct_from_c1"] = True
        if identity == c1_identity:
            rec["distinct_from_c1"] = False
            rec["status"] = "NOT_DISTINCT_FROM_C1"
            rec["AUTH_RESULT"] = rec["status"]
            rec["live_auth_proven"] = False
            return rec
        if rec["distinct_from_c1"] and (quota_out.get("ok") or cfg.get("ok")):
            rec["status"] = "REACHABLE"
            rec["live_auth_proven"] = True
            rec["AUTH_RESULT"] = "REACHABLE"
            rec["QUOTA_RESULT"] = {"quota_ok": bool(quota_out.get("ok"))}
            return rec
        rec["status"] = "PARTIAL"
        rec["AUTH_RESULT"] = "PARTIAL"
        rec["live_auth_proven"] = False
        return rec
    if rec["credential_file_present"]:
        rec["status"] = "PARTIAL"
        rec["AUTH_RESULT"] = "PARTIAL"
        rec["reason"] = "CREDENTIAL_FILE_PRESENT_LIVE_PROBE_SKIPPED"
        return rec
    if rec["candidate_dir_present"] or rec["browser_profile_hint_present"]:
        rec["status"] = "SEPARATE_PROFILE_CANDIDATE_PRESENT"
        rec["AUTH_RESULT"] = "SEPARATE_PROFILE_CANDIDATE_PRESENT"
        rec["live_auth_proven"] = False
        rec["distinct_from_c1"] = False
        return rec
    rec["status"] = "AUTH_REQUIRED"
    rec["AUTH_RESULT"] = "AUTH_REQUIRED"
    return rec


def _probe_oracle() -> dict[str, Any]:
    cfg = HOME / ".oci" / "config"
    rec: dict[str, Any] = {
        "account_id": "ORACLE_01",
        "status": "AUTH_REQUIRED",
        "cli_present": bool(shutil.which("oci")),
        "config_present": cfg.is_file(),
        "catalog_ne_entitlement": True,
        "gpu_sku": UNOBSERVED,
        "gpu_vram": UNOBSERVED,
        "IDENTITY_PROOF": UNOBSERVED,
        "AUTH_RESULT": "AUTH_REQUIRED",
        "QUOTA_RESULT": {},
        "REDACTED": True,
        "PROFILE_LABEL": "ORACLE_01",
        "account_eligible_gpu": False,
    }
    if not cfg.is_file():
        rec["reason"] = "OCI_CONFIG_ABSENT"
        return rec
    if not rec["cli_present"]:
        rec["status"] = "PARTIAL"
        rec["AUTH_RESULT"] = "PARTIAL"
        rec["reason"] = "OCI_CONFIG_PRESENT_CLI_ABSENT"
        return rec
    ns = _run_cli(["oci", "os", "ns", "get"], timeout=20)
    if ns.get("ok"):
        rec["status"] = "REACHABLE"
        rec["AUTH_RESULT"] = "REACHABLE"
        rec["IDENTITY_PROOF"] = "oci-namespace-observed"
        rec["live_auth_proven"] = True
    else:
        rec["status"] = "PARTIAL"
        rec["AUTH_RESULT"] = "PARTIAL"
        rec["reason"] = "OCI_NAMESPACE_PROBE_FAILED"
    return rec


def _probe_colab() -> dict[str, Any]:
    adc_paths = [
        HOME / "AppData" / "Roaming" / "gcloud" / "application_default_credentials.json",
        HOME / ".config" / "gcloud" / "application_default_credentials.json",
    ]
    adc_present = any(p.is_file() for p in adc_paths)
    rec: dict[str, Any] = {
        "account_id": "COLAB_01",
        "status": "AUTH_REQUIRED",
        "GOOGLE_AUTH": "ADC_PRESENT" if adc_present else "ABSENT",
        "GOOGLE_CLOUD_ACCESS": UNOBSERVED,
        "COLAB_ACCESS": UNOBSERVED,
        "COLAB_GPU_ENTITLEMENT": UNOBSERVED,
        "gcloud_cli": bool(shutil.which("gcloud")),
        "IDENTITY_PROOF": UNOBSERVED,
        "AUTH_RESULT": "AUTH_REQUIRED",
        "QUOTA_RESULT": {},
        "REDACTED": True,
        "PROFILE_LABEL": "COLAB_01",
        "gpu_sku": UNOBSERVED,
        "gpu_vram": UNOBSERVED,
        "account_eligible_gpu": False,
        "ADC_NE_COLAB_ACCESS": True,
    }
    return rec


def _probe_local() -> dict[str, Any]:
    rec: dict[str, Any] = {"account_id": "LOCAL_AG", "status": "REACHABLE"}
    try:
        du = shutil.disk_usage("C:/")
        rec["disk_total_gb"] = round(du.total / (1024**3), 3)
        rec["disk_used_gb"] = round(du.used / (1024**3), 3)
        rec["disk_free_gb"] = round(du.free / (1024**3), 3)
    except OSError:
        rec["disk_total_gb"] = UNKNOWN
        rec["disk_free_gb"] = UNKNOWN
    try:
        import ctypes

        class MEM(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        mem = MEM()
        mem.dwLength = ctypes.sizeof(MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
        rec["ram_total_gb"] = round(mem.ullTotalPhys / (1024**3), 3)
        rec["ram_avail_gb"] = round(mem.ullAvailPhys / (1024**3), 3)
    except Exception:
        rec["ram_total_gb"] = UNKNOWN
        rec["ram_avail_gb"] = UNKNOWN
    rec["c5"] = _tcp("127.0.0.1", 8766)
    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    ollama_url = ollama_host if "://" in ollama_host else f"http://{ollama_host}"
    parsed_ollama = urllib.parse.urlparse(ollama_url)
    ollama_port = parsed_ollama.port or (443 if parsed_ollama.scheme == "https" else 11434)
    rec["ollama"] = _tcp(parsed_ollama.hostname or "127.0.0.1", ollama_port)
    rec["ollama_endpoint"] = f"{parsed_ollama.scheme}://{parsed_ollama.hostname}:{ollama_port}"
    rec["mcp"] = _tcp("127.0.0.1", 8788)
    rec["ninerouter"] = _tcp("127.0.0.1", 20128)
    rec["execution_blocked_by_memory"] = True
    rec["model_storage_allowed"] = MODEL_WEIGHTS_LOCAL
    rec["qwen35_present"] = False
    try:
        tags = _http_json(f"{ollama_url}/api/tags", {})
        names = [m.get("name") for m in ((tags.get("json") or {}).get("models") or [])]
        rec["ollama_http_status"] = tags.get("http")
        rec["ollama_model_count"] = len(names)
        rec["qwen35_present"] = any(QWEN_ID in str(n) for n in names)
        rec["ollama_names"] = names
    except Exception as exc:
        rec["ollama_http_status"] = "UNAVAILABLE"
        rec["ollama_probe_error"] = type(exc).__name__
        rec["ollama_model_count"] = UNKNOWN
        rec["ollama_names"] = []
    rec["status"] = "REACHABLE" if rec.get("c5") == "SUCCESS" else "PARTIAL"
    rec["paid"] = False
    return rec


def _probe_9router() -> dict[str, Any]:
    rec = {
        "provider_type": "MODEL_ROUTING_GATEWAY",
        "endpoint": "LOCAL_ONLY",
        "RESOURCE_AUTHORITY": False,
        "health": UNKNOWN,
        "accounts_connected": UNKNOWN,
        "models_visible": UNKNOWN,
        "catalog_model_names": UNKNOWN,
        "locally_available_weights": 0,
        "executable_routed_models": 0,
        "bind": "127.0.0.1:20128",
    }
    if _tcp("127.0.0.1", 20128) != "SUCCESS":
        rec["health"] = "OFFLINE"
        return rec
    health = _http_json("http://127.0.0.1:20128/api/health", {})
    rec["health"] = "ok" if health.get("http") == 200 else "DEGRADED"
    models = _http_json("http://127.0.0.1:20128/v1/models", {})
    data = (models.get("json") or {}).get("data") or []
    rec["models_visible"] = len(data)
    rec["catalog_model_names"] = len(data)
    rec["accounts_connected"] = 0
    rec["locally_available_weights"] = 0
    rec["executable_routed_models"] = 0
    rec["catalog_ne_connected_providers"] = True
    rec["paid_providers_connected"] = False
    return rec


def run_live_probes(*, live: bool = True) -> dict[str, Any]:
    auth = discover_auth()
    probes: dict[str, Any] = {}

    def _iso(account: str, fn: Any) -> dict[str, Any]:
        try:
            return fn()
        except Exception as exc:
            return {"account_id": account, "status": "UNAVAILABLE", "reason": type(exc).__name__, "PROBE_FAIL_NE_ABSENT": True}

    probes["LOCAL_AG"] = _iso("LOCAL_AG", _probe_local)
    probes["NINEROUTER"] = _iso("NINEROUTER", _probe_9router)
    if live:
        probes["KAGGLE_C1"] = _iso("KAGGLE_C1", _probe_kaggle_c1)
        probes["LIGHTNING_01"] = _iso("LIGHTNING_01", _probe_lightning)
        probes["MODAL_01"] = _iso("MODAL_01", _probe_modal_presence)
    else:
        probes["KAGGLE_C1"] = {"account_id": "KAGGLE_C1", "status": "SKIPPED"}
        probes["LIGHTNING_01"] = {"account_id": "LIGHTNING_01", "status": "SKIPPED"}
        probes["MODAL_01"] = {"account_id": "MODAL_01", "status": "SKIPPED"}
    probes["KAGGLE_PARTNER"] = {
        "account_id": "KAGGLE_PARTNER",
        "status": "BLOCKED_C1_ACTION",
        "AUTH_RESULT": "BLOCKED_C1_ACTION",
        "PROBE_SKIPPED": True,
        "isolated_from": "KAGGLE_C1",
        "copied_from_c1": False,
        "live_auth_proven": False,
        "distinct_from_c1": False,
        "reason": "WAVE06_CLOSURE_NO_REPEAT_PROBE",
    }
    probes["ORACLE_01"] = {
        "account_id": "ORACLE_01",
        "status": "BLOCKED_C1_ACTION",
        "AUTH_RESULT": "BLOCKED_C1_ACTION",
        "PROBE_SKIPPED": True,
        "reason": "WAVE06_CLOSURE_NO_REPEAT_PROBE",
    }
    probes["COLAB_01"] = {
        "account_id": "COLAB_01",
        "status": "BLOCKED_C1_ACTION",
        "AUTH_RESULT": "BLOCKED_C1_ACTION",
        "PROBE_SKIPPED": True,
        "GOOGLE_AUTH": "ABSENT",
        "COLAB_ACCESS": UNOBSERVED,
        "COLAB_GPU_ENTITLEMENT": UNOBSERVED,
        "ADC_NE_COLAB_ACCESS": True,
        "reason": "WAVE06_CLOSURE_NO_REPEAT_PROBE",
    }
    now = _now()
    verified_ok = {
        "REACHABLE",
        "PARTIAL",
        "REACHABLE_CREDENTIAL_PRESENT",
        "SEPARATE_PROFILE_CANDIDATE_PRESENT",
    }
    for row in auth:
        live_rec = probes.get(row["account_id"]) or {}
        if live_rec.get("status") in verified_ok:
            row["last_verified"] = now
            row["session_state"] = live_rec.get("status")
    payload = mask_record({"auth": auth, "probes": probes, "observed_at": now, "PAID_RESOURCE_CREATED": False})
    assert_no_secrets(payload)
    return payload


def apply_live_overlay(world: dict[str, Any], live_state: dict[str, Any]) -> dict[str, Any]:
    probes = live_state.get("probes") or {}
    auth = {a["account_id"]: a for a in live_state.get("auth") or []}
    now = live_state.get("observed_at") or utc()
    for acc in world.get("accounts") or []:
        aid = acc["account_id"]
        pr = probes.get(aid) or {}
        au = auth.get(aid) or {}
        status = pr.get("status")
        if status in {None, "SKIPPED"}:
            status = au.get("session_state") or acc.get("status")
        if aid == "KAGGLE_C1" and status == "AUTH_REQUIRED" and au.get("kaggle_oauth_credentials_present"):
            status = "PARTIAL"
        if status in {"CONFIG_PRESENT", "CREDENTIAL_FILE_PRESENT", "ENV_PRESENT"}:
            status = "PARTIAL"
        if aid == "MODAL_01" and (pr.get("token_fields_present") or status == "REACHABLE_CREDENTIAL_PRESENT"):
            if status != "REACHABLE":
                status = "REACHABLE_CREDENTIAL_PRESENT"
        if status == "FILE_ABSENT_NOT_PROOF_OF_NO_AUTH":
            status = "AUTH_REQUIRED"
        if status == "SEPARATE_PROFILE_CANDIDATE_PRESENT":
            status = "PARTIAL"
        if status == "NOT_DISTINCT_FROM_C1":
            status = "AUTH_REQUIRED"
        acc["status"] = status
        acc["auth_method"] = au.get("auth_method") or pr.get("auth_method") or UNKNOWN
        if au.get("credential_ref"):
            acc["credential_ref"] = au["credential_ref"]
        acc["last_verified_at"] = au.get("last_verified") or acc.get("last_verified_at") or UNKNOWN
        acc["ACCOUNT_REACHABLE"] = status in {"REACHABLE", "REACHABLE_CREDENTIAL_PRESENT"}
        acc["AUTH_REQUIRED_NE_ABSENT"] = True
        if status == "BLOCKED_C1_ACTION":
            acc["BLOCKED_C1_ACTION"] = True
            acc["ACCOUNT_REACHABLE"] = False
        if aid == "KAGGLE_C1" and pr.get("username_bound") == "greenylife":
            acc["plan"] = "KAGGLE_FREE_OR_STANDARD"
            acc["free_tier_status"] = "GPU_QUOTA_OBSERVED"
            acc["accelerator_types"] = pr.get("accelerator_types") or []
        if aid == "LIGHTNING_01" and pr.get("status") == "REACHABLE":
            acc["plan"] = "LIGHTNING_PERSONAL_ORG"
            acc["billing_mode"] = "CREDITS"
            acc["studio_count"] = pr.get("studio_count")
        if aid == "LOCAL_AG":
            acc["status"] = pr.get("status") or "REACHABLE"
            acc["ACCOUNT_REACHABLE"] = True
        if aid == "KAGGLE_PARTNER":
            acc["live_auth_proven"] = bool(pr.get("live_auth_proven"))
            acc["distinct_from_c1"] = bool(pr.get("distinct_from_c1"))
            acc["copied_from_c1"] = bool(pr.get("copied_from_c1"))
            acc["DISPATCH_ALLOWED"] = bool(
                acc["live_auth_proven"] and acc["distinct_from_c1"] and not acc["copied_from_c1"] and status in {"REACHABLE", "REACHABLE_CREDENTIAL_PRESENT"}
            )
        if aid == "COLAB_01":
            acc["GOOGLE_AUTH"] = pr.get("GOOGLE_AUTH") or "ABSENT"
            acc["GOOGLE_CLOUD_ACCESS"] = pr.get("GOOGLE_CLOUD_ACCESS") or UNOBSERVED
            acc["COLAB_ACCESS"] = pr.get("COLAB_ACCESS") or UNOBSERVED
            acc["COLAB_GPU_ENTITLEMENT"] = pr.get("COLAB_GPU_ENTITLEMENT") or UNOBSERVED
            if pr.get("status") == "BLOCKED_C1_ACTION":
                acc["status"] = "BLOCKED_C1_ACTION"
                acc["ACCOUNT_REACHABLE"] = False
            elif pr.get("COLAB_ACCESS") not in {"PROVEN", "REACHABLE", True}:
                acc["status"] = "AUTH_REQUIRED"
                acc["ACCOUNT_REACHABLE"] = False
        if aid == "MODAL_01":
            acc["gpu_entitlement"] = pr.get("gpu_entitlement") or UNOBSERVED
            acc["CATALOG_NE_ENTITLEMENT"] = True

    world["accelerators"] = [g for g in (world.get("accelerators") or []) if g.get("observation_kind") != "LIVE"]
    for gpu in world.get("accelerators") or []:
        gpu.setdefault("gpu_class", "CATALOG_GPU")
        gpu.setdefault("observation_kind", "CATALOG")

    kag = probes.get("KAGGLE_C1") or {}
    if kag.get("gpu_quota"):
        gq = kag["gpu_quota"]
        world["quotas"] = [q for q in world.get("quotas") or [] if not (q.get("account_id") == "KAGGLE_C1" and q.get("resource_type") == "gpu_hours")]
        world["quotas"].append(
            quota(
                quota_id="KAGGLE_C1:gpu-weekly",
                provider_id="KAGGLE",
                account_id="KAGGLE_C1",
                service_id="KAGGLE_C1:notebook",
                resource_type="gpu_hours",
                limit=gq.get("limit"),
                used=gq.get("used"),
                remaining=gq.get("remaining"),
                unit="hours",
                reset_period="WEEKLY",
                reset_at=str(gq.get("reset_at") or UNKNOWN),
            )
        )
        tq = kag.get("tpu_quota") or {}
        world["quotas"].append(
            quota(
                quota_id="KAGGLE_C1:tpu-weekly",
                provider_id="KAGGLE",
                account_id="KAGGLE_C1",
                service_id="KAGGLE_C1:notebook",
                resource_type="tpu_hours",
                limit=tq.get("limit"),
                used=tq.get("used"),
                remaining=tq.get("remaining"),
                unit="hours",
                reset_period="WEEKLY",
                reset_at=str(tq.get("reset_at") or UNKNOWN),
            )
        )
        world["accelerators"].append(
            {
                "schema": world["accelerators"][0]["schema"] if world.get("accelerators") else "raios.resource-fabric.v1",
                "kind": "AcceleratorResource",
                "resource_id": "KAGGLE_C1:gpu-eligible-live",
                "provider_id": "KAGGLE",
                "account_id": "KAGGLE_C1",
                "gpu_class": "ACCOUNT_ELIGIBLE_GPU",
                "observation_kind": "LIVE",
                "available": bool(kag.get("account_eligible_gpu")),
                "gpu_model": UNKNOWN,
                "gpu_vram_gb": UNKNOWN,
                "weekly_quota": gq.get("remaining"),
                "ZERO_QUOTA_NE_UNAVAILABLE": True,
            }
        )
        world["accelerators"].append(
            {
                "schema": "raios.resource-fabric.v1",
                "kind": "AcceleratorResource",
                "resource_id": "KAGGLE_C1:active-session-gpu",
                "provider_id": "KAGGLE",
                "account_id": "KAGGLE_C1",
                "gpu_class": "ACTIVE_SESSION_GPU",
                "observation_kind": "LIVE",
                "available": bool(kag.get("active_session_gpu")),
                "gpu_model": UNKNOWN,
                "gpu_vram_gb": UNKNOWN,
            }
        )
        used_gb = UNKNOWN
        if isinstance(kag.get("dataset_used_bytes"), (int, float)):
            used_gb = round(float(kag["dataset_used_bytes"]) / (1024**3), 6)
        for st in world.get("storage") or []:
            if st.get("storage_id") == "KAGGLE_C1:dataset_storage":
                st["capacity_used_gb"] = used_gb
                st["observation_kind"] = "LIVE_USED_ONLY"
                st["cli_access"] = True

    lit = probes.get("LIGHTNING_01") or {}
    if lit.get("status") == "REACHABLE":
        rem = lit.get("credits_remaining")
        world["credits"] = [c for c in world.get("credits") or [] if c.get("account_id") != "LIGHTNING_01"]
        world["credits"].append(
            credit(
                credit_id="LIGHTNING_01:org-credits",
                provider_id="LIGHTNING",
                account_id="LIGHTNING_01",
                remaining_value=rem,
                original_value=UNKNOWN,
                currency="CREDIT",
                restrictions=["CREDIT_NE_CASH", "NOT_USD_CASH"],
            )
        )
        used_gb = UNKNOWN
        free_gb = UNKNOWN
        try:
            used_gb = round(float(lit.get("storage_used_bytes")) / (1024**3), 6)
        except (TypeError, ValueError):
            pass
        try:
            free_gb = round(float(lit.get("free_storage_bytes")) / (1024**3), 3)
        except (TypeError, ValueError):
            pass
        for st in world.get("storage") or []:
            if st.get("storage_id") == "LIGHTNING_01:file_storage":
                st["capacity_used_gb"] = used_gb
                st["free_quota_gb"] = free_gb
                st["capacity_total_gb"] = UNKNOWN
                st["capacity_free_gb"] = UNKNOWN
                st["observation_kind"] = "LIVE_USED_AND_FREE_QUOTA"
                st["model_weights_suitable"] = True
        world["quotas"].append(
            quota(
                quota_id="LIGHTNING_01:free-drive",
                provider_id="LIGHTNING",
                account_id="LIGHTNING_01",
                service_id="LIGHTNING_01:studio",
                resource_type="drive_bytes",
                limit=lit.get("free_storage_bytes"),
                used=lit.get("storage_used_bytes"),
                remaining=UNKNOWN,
                unit="bytes",
            )
        )
        world["compute"] = [
            {**c, "current_instances": lit.get("studio_count"), "observation_kind": "LIVE"} if c.get("resource_id") == "LIGHTNING_01:studio" else c
            for c in world.get("compute") or []
        ]

    loc = probes.get("LOCAL_AG") or {}
    if loc:
        for cmp in world.get("compute") or []:
            if cmp.get("account_id") == "LOCAL_AG":
                cmp["ram_gb"] = loc.get("ram_total_gb", UNKNOWN)
                cmp["ram_avail_gb"] = loc.get("ram_avail_gb", UNKNOWN)
                cmp["execution_blocked_by_memory"] = bool(loc.get("execution_blocked_by_memory", True))
                cmp["vcpu"] = UNKNOWN
                cmp["observation_kind"] = "LIVE"
        for st in world.get("storage") or []:
            if st.get("storage_id") == "LOCAL_AG:workspace-disk":
                st["capacity_total_gb"] = loc.get("disk_total_gb", UNKNOWN)
                st["capacity_used_gb"] = loc.get("disk_used_gb", UNKNOWN)
                st["capacity_free_gb"] = loc.get("disk_free_gb", UNKNOWN)
                st["model_weights_suitable"] = False
                st["observation_kind"] = "LIVE"

    # Modal catalog prices (public page). Not account remaining.
    world["pricing"] = [p for p in world.get("pricing") or [] if p.get("account_id") != "MODAL_01"]
    for model, per_sec in MODAL_CATALOG_GPU_SEC.items():
        world["pricing"].append(
            price(
                price_id=f"MODAL_01:catalog-{model}",
                kind="CATALOG_PRICE",
                provider_id="MODAL",
                account_id="MODAL_01",
                resource_type=f"gpu:{model}",
                amount=round(per_sec * 3600.0, 6),
                pricing_unit="HOUR",
                source="https://modal.com/pricing",
                observed_at=now,
            )
        )
    world["pricing"].append(
        price(
            price_id="MODAL_01:catalog-volume",
            kind="CATALOG_PRICE",
            provider_id="MODAL",
            account_id="MODAL_01",
            resource_type="file_storage",
            amount=MODAL_VOLUME_GIB_MONTH,
            pricing_unit="GIB_MONTH",
            source="https://modal.com/pricing",
            observed_at=now,
        )
    )
    world["pricing"].append(
        price(
            price_id="MODAL_01:starter-credit-catalog",
            kind="FREE_TIER_PRICE",
            provider_id="MODAL",
            account_id="MODAL_01",
            resource_type="monthly_credit",
            amount=30,
            pricing_unit="USD_MONTH",
            source="https://modal.com/pricing",
            observed_at=now,
        )
    )
    kag_rem = (kag.get("gpu_quota") or {}).get("remaining")
    world["pricing"] = [p for p in world.get("pricing") or [] if p.get("price_id") != "KAGGLE_C1:gpu-free-tier"]
    world["pricing"].append(
        price(
            price_id="KAGGLE_C1:gpu-free-tier",
            kind="FREE_TIER_PRICE",
            provider_id="KAGGLE",
            account_id="KAGGLE_C1",
            resource_type="gpu",
            amount=0,
            pricing_unit="HOUR",
            source="kaggle quota CLI; remaining_hours=" + str(kag_rem),
            observed_at=now,
        )
    )
    world["gateways"] = [probes.get("NINEROUTER") or {}]
    world["live_probes"] = probes
    assert_no_secrets(world)
    return world


def service_estate(world: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    acc = {a["account_id"]: a for a in world.get("accounts") or []}
    for svc in world.get("services") or []:
        aid = svc.get("account_id")
        st = (acc.get(aid) or {}).get("status")
        classification = "UNKNOWN"
        if st == "AUTH_REQUIRED":
            classification = "UNKNOWN"
        elif svc.get("enabled") and svc.get("available"):
            q = svc.get("quota_available")
            if q == 0:
                classification = "AVAILABLE_ZERO_QUOTA"
            else:
                classification = "ENABLED"
        elif svc.get("available") and not svc.get("enabled"):
            classification = "AVAILABLE_DISABLED"
        elif svc.get("available"):
            classification = "AVAILABLE_UNUSED"
        out.append({"service_id": svc.get("service_id"), "account_id": aid, "classification": classification, "AUTH_REQUIRED_NE_ABSENT": True})
    return out


def cost_simulation(world: dict[str, Any], live_state: dict[str, Any]) -> dict[str, Any]:
    kag = (live_state.get("probes") or {}).get("KAGGLE_C1") or {}
    rem = (kag.get("gpu_quota") or {}).get("remaining")
    rem_n = rem if isinstance(rem, (int, float)) else UNKNOWN
    rows = {}
    for aid in TARGET_ACCOUNTS:
        gpu_rate = UNKNOWN
        store_rate = UNKNOWN
        egress_rate = UNKNOWN
        compute_rate = UNKNOWN
        credits = [c for c in world.get("credits") or [] if c.get("account_id") == aid]
        free_h = 0
        if aid == "KAGGLE_C1":
            gpu_rate = 0
            free_h = rem_n if rem_n is not UNKNOWN else 0
        if aid == "LOCAL_AG":
            compute_rate = 0
            gpu_rate = 0
            store_rate = 0
            egress_rate = 0
        if aid == "MODAL_01":
            gpu_rate = round(MODAL_CATALOG_GPU_SEC["T4"] * 3600.0, 6)
            store_rate = MODAL_VOLUME_GIB_MONTH
        sim = {
            "compute_1h": estimate(scenario="COST_1H", compute_rate=compute_rate, free_tier_hours=free_h),
            "compute_10h": estimate(scenario="COST_10_HOURS", compute_rate=compute_rate, free_tier_hours=free_h),
            "compute_100h": estimate(scenario="COST_100_HOURS", compute_rate=compute_rate, free_tier_hours=free_h),
            "gpu_1h": estimate(scenario="GPU_1H", accelerator_rate=gpu_rate, free_tier_hours=free_h, credits=credits),
            "gpu_10h": estimate(scenario="GPU_10H", accelerator_rate=gpu_rate, free_tier_hours=free_h, credits=credits),
            "gpu_100h": estimate(scenario="GPU_100H", accelerator_rate=gpu_rate, free_tier_hours=free_h, credits=credits),
            "storage_10gb": estimate(scenario="STORAGE_10GB", storage_gb_month=store_rate),
            "storage_50gb": estimate(scenario="STORAGE_50GB", storage_gb_month=store_rate),
            "storage_100gb": estimate(scenario="STORAGE_100GB", storage_gb_month=store_rate),
            "storage_500gb": estimate(scenario="STORAGE_500GB", storage_gb_month=store_rate),
            "storage_1tb": estimate(scenario="STORAGE_1TB", storage_gb_month=store_rate),
            "egress_10gb": estimate(scenario="EGRESS_10GB", egress_gb_rate=egress_rate),
            "egress_100gb": estimate(scenario="EGRESS_100GB", egress_gb_rate=egress_rate),
            "egress_1tb": estimate(scenario="EGRESS_1TB", egress_gb_rate=egress_rate),
            "persistent_24_7": estimate(scenario="COST_24_7", compute_rate=compute_rate, credits=credits),
        }
        # Kaggle 100h exceeds remaining free hours → remaining hours UNKNOWN paid rate
        if aid == "KAGGLE_C1" and rem_n is not UNKNOWN and float(rem_n) < 100:
            sim["gpu_100h"]["gross"] = UNKNOWN
            sim["gpu_100h"]["net"] = UNKNOWN
            sim["gpu_100h"]["note"] = "FREE_HOURS_INSUFFICIENT_PAID_RATE_UNKNOWN"
        rows[aid] = sim
    return {"schema": "raios.resource-fabric.cost-sim.v1", "accounts": rows, "PAID_RESOURCE_ACTIVATED": False}


def model_hosting_fit(world: dict[str, Any], live_state: dict[str, Any]) -> dict[str, Any]:
    probes = live_state.get("probes") or {}
    acc = {a["account_id"]: a for a in world.get("accounts") or []}
    out = {}
    for aid in TARGET_ACCOUNTS:
        st = (acc.get(aid) or {}).get("status")
        reachable = st in {"REACHABLE", "REACHABLE_CREDENTIAL_PRESENT", "PARTIAL"}
        row = {
            "account_id": aid,
            "CAN_STORE_MODEL_WEIGHTS": False if aid == "LOCAL_AG" else (UNKNOWN if not reachable or st == "AUTH_REQUIRED" else UNKNOWN),
            "CAN_RUN_INFERENCE": UNKNOWN,
            "CAN_RUN_GPU_INFERENCE": UNKNOWN,
            "CAN_RUN_CPU_INFERENCE": UNKNOWN,
            "CAN_SERVE_PERSISTENT_ENDPOINT": UNKNOWN,
            "CAN_RUN_EPHEMERAL_ENDPOINT": UNKNOWN,
            "CAN_RUN_OLLAMA": UNKNOWN,
            "CAN_RUN_LLAMA_CPP": UNKNOWN,
            "CAN_RUN_VLLM": UNKNOWN,
            "CAN_RUN_CONTAINER": UNKNOWN,
            "CAN_RUN_DOCKER": UNKNOWN,
        }
        if aid == "LOCAL_AG":
            loc = probes.get("LOCAL_AG") or {}
            row.update(
                {
                    "CAN_STORE_MODEL_WEIGHTS": False,
                    "CAN_RUN_INFERENCE": True,
                    "CAN_RUN_GPU_INFERENCE": False,
                    "CAN_RUN_CPU_INFERENCE": True,
                    "CAN_SERVE_PERSISTENT_ENDPOINT": loc.get("c5") == "SUCCESS",
                    "CAN_RUN_EPHEMERAL_ENDPOINT": True,
                    "CAN_RUN_OLLAMA": loc.get("ollama") == "SUCCESS",
                    "CAN_RUN_LLAMA_CPP": UNKNOWN,
                    "CAN_RUN_VLLM": False,
                    "CAN_RUN_CONTAINER": UNKNOWN,
                    "CAN_RUN_DOCKER": UNKNOWN,
                    "LOCAL_AG_MODEL_STORAGE_ALLOWED": False,
                    "LOCAL_AG_EXECUTION_BLOCKED_BY_MEMORY": True,
                }
            )
        if aid == "KAGGLE_C1" and st == "REACHABLE":
            row.update(
                {
                    "CAN_STORE_MODEL_WEIGHTS": UNKNOWN,
                    "CAN_RUN_INFERENCE": UNKNOWN,
                    "CAN_RUN_GPU_INFERENCE": True,
                    "CAN_RUN_CPU_INFERENCE": True,
                    "CAN_SERVE_PERSISTENT_ENDPOINT": False,
                    "CAN_RUN_EPHEMERAL_ENDPOINT": True,
                    "CAN_RUN_CONTAINER": False,
                    "CAN_RUN_DOCKER": False,
                    "CAN_RUN_VLLM": UNKNOWN,
                    "note": "DATASET_TOTAL_QUOTA_UNOBSERVED; CATALOG_GPU_NE_CURRENT_SKU",
                }
            )
        if aid == "LIGHTNING_01" and st == "REACHABLE":
            free_gb = UNKNOWN
            try:
                free_gb = round(float((probes.get("LIGHTNING_01") or {}).get("free_storage_bytes")) / (1024**3), 3)
            except (TypeError, ValueError):
                pass
            row.update(
                {
                    "CAN_STORE_MODEL_WEIGHTS": False if free_gb is not UNKNOWN and float(free_gb) < QWEN_GB else UNKNOWN,
                    "CAN_RUN_GPU_INFERENCE": UNKNOWN,
                    "CAN_RUN_CPU_INFERENCE": True,
                    "CAN_SERVE_PERSISTENT_ENDPOINT": True,
                    "CAN_RUN_EPHEMERAL_ENDPOINT": True,
                    "CAN_RUN_CONTAINER": UNKNOWN,
                    "CAN_RUN_DOCKER": UNKNOWN,
                    "CAN_RUN_OLLAMA": UNKNOWN,
                    "CAN_RUN_VLLM": UNKNOWN,
                }
            )
        if aid == "MODAL_01" and st in {"PARTIAL", "REACHABLE", "REACHABLE_CREDENTIAL_PRESENT"}:
            row.update(
                {
                    "CAN_STORE_MODEL_WEIGHTS": UNKNOWN,
                    "CAN_RUN_GPU_INFERENCE": UNKNOWN,
                    "CAN_RUN_CONTAINER": True,
                    "CAN_RUN_DOCKER": True,
                    "CAN_RUN_VLLM": UNKNOWN,
                    "CAN_SERVE_PERSISTENT_ENDPOINT": UNKNOWN,
                    "CAN_RUN_EPHEMERAL_ENDPOINT": True,
                    "note": "TOKEN_PRESENT_ACCOUNT_CAPACITY_UNOBSERVED",
                }
            )
        if st == "AUTH_REQUIRED":
            row["note"] = "AUTH_REQUIRED_NE_ABSENT"
        out[aid] = row
    return out


def qwen35b_placement(world: dict[str, Any], live_state: dict[str, Any], fit: dict[str, Any]) -> dict[str, Any]:
    loc = (live_state.get("probes") or {}).get("LOCAL_AG") or {}
    store = []
    run = []
    efficient = []
    serve = []
    if fit.get("KAGGLE_C1", {}).get("CAN_STORE_MODEL_WEIGHTS") is True:
        store.append("KAGGLE_C1:dataset_storage")
    elif (world.get("accounts") and any(a.get("account_id") == "KAGGLE_C1" and a.get("status") == "REACHABLE" for a in world["accounts"])):
        store.append("KAGGLE_C1:dataset_storage?QUOTA_TOTAL_UNKNOWN")
    if fit.get("LIGHTNING_01", {}).get("CAN_STORE_MODEL_WEIGHTS") is True:
        store.append("LIGHTNING_01:file_storage")
    if fit.get("KAGGLE_C1", {}).get("CAN_RUN_GPU_INFERENCE") is True:
        run.append("KAGGLE_C1:ACCOUNT_ELIGIBLE_GPU")
    kag_catalog = [g for g in world.get("accelerators") or [] if g.get("account_id") == "KAGGLE_C1" and g.get("gpu_class") == "CATALOG_GPU"]
    for g in kag_catalog:
        vram = g.get("gpu_vram_gb")
        if isinstance(vram, (int, float)) and float(vram) >= 24:
            efficient.append(g.get("resource_id"))
        elif isinstance(vram, (int, float)) and float(vram) < QWEN_GB:
            pass
    if fit.get("LIGHTNING_01", {}).get("CAN_SERVE_PERSISTENT_ENDPOINT") is True:
        serve.append("LIGHTNING_01:studio")
    return {
        "model_id": QWEN_ID,
        "MODEL_SIZE_APPROX_GB": QWEN_GB,
        "LOCAL_AG_EXECUTION_BLOCKED_BY_MEMORY": True,
        "local_ram_gb": loc.get("ram_total_gb", UNKNOWN),
        "LOCAL_RUN_FORBIDDEN": True,
        "REDOWNLOAD_FORBIDDEN": True,
        "WHERE_CAN_STORE": store or [UNKNOWN],
        "WHERE_CAN_RUN": run or [UNKNOWN],
        "WHERE_CAN_RUN_EFFICIENTLY": efficient or [UNKNOWN],
        "WHERE_CAN_SERVE": serve or [UNKNOWN],
        "ESTIMATED_COST": UNKNOWN,
        "BEST_CURRENT_PLACEMENT": {
            "CONTROL": "LOCAL_AG",
            "STORAGE": store[0] if store else UNKNOWN,
            "INFERENCE": run[0] if run else UNKNOWN,
            "reason": "No live >=24GB VRAM observed; Kaggle eligible GPU hours exist but SKU/VRAM live-unobserved; do not migrate.",
        },
        "MODEL_WEIGHT_TRANSFER_EXECUTED": False,
        "LOCAL_MODEL_DELETE_EXECUTED": False,
    }


def bind_live_accounts(world: dict[str, Any], *, live: bool | None = None) -> dict[str, Any]:
    if live is None:
        live = os.environ.get("RAIOS_RESOURCE_LIVE", "1") != "0"
    before = count_unknown_fields(world)
    state = run_live_probes(live=live)
    apply_live_overlay(world, state)
    after = count_unknown_fields(world)
    reduced = {k: before[k] - after[k] for k in before}
    world["unknown_before"] = before
    world["unknown_after"] = after
    world["unknown_reduced"] = reduced
    world["live_state"] = state
    return state


def build_wave02_views(world: dict[str, Any]) -> dict[str, Any]:
    live_state = world.get("live_state") or {"auth": discover_auth(), "probes": {}}
    fit = model_hosting_fit(world, live_state)
    qwen = qwen35b_placement(world, live_state, fit)
    rec = recompose_v2(world)
    acc = world.get("accounts") or []
    return mask_record(
        {
            "ACCOUNT-AUTH-BINDINGS.json": live_state.get("auth") or discover_auth(),
            "LIVE-COMPUTE.json": world.get("compute") or [],
            "LIVE-ACCELERATORS.json": world.get("accelerators") or [],
            "LIVE-STORAGE.json": world.get("storage") or [],
            "LIVE-SERVICES.json": {"services": world.get("services") or [], "classification": service_estate(world)},
            "LIVE-QUOTAS.json": world.get("quotas") or [],
            "LIVE-CREDITS.json": world.get("credits") or [],
            "LIVE-PRICING.json": world.get("pricing") or [],
            "LIVE-COST-SIMULATION.json": cost_simulation(world, live_state),
            "MODEL-HOSTING-FIT.json": fit,
            "QWEN35B-PLACEMENT.json": qwen,
            "9ROUTER-BINDING.json": ((world.get("gateways") or [{}])[0]),
            "RESOURCE-RECOMPOSITION-V2.json": rec,
            "UNKNOWN-REDUCTION.json": {
                "BEFORE": world.get("unknown_before"),
                "AFTER": world.get("unknown_after"),
                "REDUCED_BY": world.get("unknown_reduced"),
                "AUTH_REQUIRED_BEFORE": 6,
                "AUTH_REQUIRED_AFTER": sum(1 for a in acc if a.get("account_id") in TARGET_ACCOUNTS and a.get("status") == "AUTH_REQUIRED"),
            },
        }
    )


def write_wave02_package(world: dict[str, Any], extra: dict[str, Any] | None = None, dest: Path | None = None) -> dict[str, Any]:
    dest = dest or WAVE02_PACKAGE
    dest.mkdir(parents=True, exist_ok=True)
    views = build_wave02_views(world)
    views.update(extra or {})
    names: list[str] = []
    for name, payload in views.items():
        path = dest / name
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n" if not isinstance(payload, str) else payload
        if isinstance(payload, str) and not name.endswith(".json"):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(text if isinstance(payload, str) else json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if not isinstance(payload, str):
                assert_no_secrets(payload)
        names.append(name)
    sha_lines = []
    for name in sorted(p.name for p in dest.iterdir() if p.is_file() and p.name != "FILES-SHA256.txt"):
        digest = hashlib.sha256((dest / name).read_bytes()).hexdigest()
        sha_lines.append(f"{digest}  {name}")
    (dest / "FILES-SHA256.txt").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")
    pkg = hashlib.sha256((dest / "FILES-SHA256.txt").read_bytes()).hexdigest()
    return {"PACKAGE": str(dest), "FILES": sorted(names), "PACKAGE_SHA256": pkg}
