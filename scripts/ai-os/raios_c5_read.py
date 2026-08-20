#!/usr/bin/env python3
"""C5 read: skim + deep on every file kind. Hash transfer. Never dump WAL. Never copy secrets."""
from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
INDEX = ROOT / ".ai-os" / "learning" / "INDEX.json"
LAST_SEARCH = ROOT / ".ai-os" / "learning" / "LAST-SEARCH.json"

SECRET_RE = re.compile(
    r"DATABASE_URL\s*=\s*\S+|APP_SESSION_SECRET\s*=\s*\S+|gl_session\s*=\s*\S+|postgres(?:ql)?://\S+",
    re.I,
)
CODE_RE = re.compile(
    r"^(?:def |class |function |export |async def |fn |pub fn |interface |type )(.+)$",
    re.M,
)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.M)
TEXT_EXT = {
    ".md", ".txt", ".rst", ".csv", ".tsv", ".html", ".xml", ".svg",
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".sh", ".bash",
    ".css", ".scss", ".less", ".vue", ".svelte", ".go", ".rs", ".java",
    ".sql", ".prisma", ".graphql", ".yml", ".yaml", ".toml", ".ini",
    ".json", ".jsonl", ".ndjson",
}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}
ARCHIVE_EXT = {".zip", ".gz", ".tgz", ".tar", ".7z", ".whl"}
PDF_EXT = {".pdf"}
SKIP_NAMES = {"tokens.local.json", ".env", ".env.local", "id_rsa", "id_ed25519"}
SKIP_PARTS = ("node_modules", ".git", ".next", "tokens.local", "__pycache__", "coverage")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def skip_path(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return True
    if path.name in {
        "DIGESTS.jsonl",
        "CANDIDATES.jsonl",
        "INDEX.json",
        "LESSONS.jsonl",
        "COMPEL.jsonl",
        "LAST-LEARN.json",
        "tokens.local.json",
    }:
        return True
    rel = str(path).replace("\\", "/")
    return any(part in rel for part in SKIP_PARTS)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_probably_text(data: bytes) -> bool:
    if not data:
        return True
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def image_meta(data: bytes) -> dict:
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return {"format": "png", "width": width, "height": height}
    if data[:2] == b"\xff\xd8":
        return {"format": "jpeg"}
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return {"format": "gif"}
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return {"format": "webp"}
    return {"format": "image"}


def classify(path: Path, data: bytes) -> str:
    ext = path.suffix.lower()
    if path.name in SKIP_NAMES or SECRET_RE.search(data.decode("utf-8", errors="ignore")[:2000] if data else ""):
        if path.name in SKIP_NAMES:
            return "secret"
    if ext in IMAGE_EXT:
        return "image"
    if ext in PDF_EXT or data[:4] == b"%PDF":
        return "pdf"
    if ext in ARCHIVE_EXT:
        return "archive"
    if ext in {".json"}:
        return "json"
    if ext in {".jsonl", ".ndjson"}:
        return "jsonl"
    if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".sh"}:
        return "code"
    if ext in {".md", ".rst"}:
        return "markdown"
    if ext in TEXT_EXT or is_probably_text(data):
        return "text"
    return "binary"


def deep_structure(kind: str, text: str) -> dict:
    if kind == "json":
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return {"parse": "invalid-json"}
        if isinstance(obj, dict):
            return {"keys": list(obj.keys())[:40], "type": "object"}
        if isinstance(obj, list):
            return {"type": "array", "n": len(obj)}
        return {"type": type(obj).__name__}
    if kind == "jsonl":
        lines = [ln for ln in text.splitlines() if ln.strip()]
        keys: list[str] = []
        if lines:
            try:
                first = json.loads(lines[0])
                if isinstance(first, dict):
                    keys = list(first.keys())[:40]
            except json.JSONDecodeError:
                pass
        return {"lines": len(lines), "first_keys": keys}
    if kind == "code":
        names = [m.group(0)[:120] for m in CODE_RE.finditer(text)]
        return {"defs": names[:40], "def_count": len(names)}
    if kind == "markdown":
        heads = [m.group(1).strip()[:160] for m in HEADING_RE.finditer(text)]
        return {"headings": heads[:40]}
    laws = sorted(set(re.findall(r"\b[A-Z][A-Z0-9_]{5,}\b", text)))
    return {"law_tokens": laws[:40], "chars": len(text)}


def read_file(path: Path, *, mode: str = "skim") -> dict:
    data = path.read_bytes()
    digest = sha256_bytes(data)
    kind = classify(path, data)
    rec: dict = {
        "schema": "raios.c5-read.v1",
        "ts": utc(),
        "from": "C5",
        "path": relpath(path),
        "kind": kind,
        "mode": mode,
        "sha256": digest,
        "bytes": len(data),
        "wal_written": False,
        "gl005_proven": False,
        "law": ["C5_READS_SKIM_AND_DEEP", "C5_READS_ALL_FILE_TYPES", "ABSORB_DIGEST_NE_WAL_DUMP"],
    }
    if kind == "secret":
        rec["secret_redacted"] = True
        rec["skim_head"] = ""
        rec["skim_tail"] = ""
        rec["status"] = "REDACTED"
        return rec
    if kind in {"image", "pdf", "archive", "binary"}:
        rec["skim_head"] = data[:16].hex()
        rec["skim_tail"] = ""
        rec["status"] = "ABSORBED"
        if kind == "image":
            rec["structure"] = image_meta(data)
        elif kind == "pdf":
            rec["structure"] = {"format": "pdf", "magic": data[:8].decode("latin-1", errors="replace")}
        else:
            rec["structure"] = {"kind": kind}
        return rec
    text = data.decode("utf-8", errors="replace")
    secret = bool(SECRET_RE.search(text))
    rec["secret_redacted"] = secret
    rec["chars"] = len(text)
    rec["lines"] = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    rec["skim_head"] = "" if secret else text[:500]
    rec["skim_tail"] = "" if secret or len(text) <= 1000 else text[-500:]
    rec["status"] = "ABSORBED"
    if mode == "deep" and not secret:
        rec["structure"] = deep_structure(kind, text)
        if len(text) > 2000:
            mid = len(text) // 2
            rec["skim_mid"] = text[mid : mid + 400]
    return rec


def search(query: str, *, use_rg: bool = True) -> dict:
    q = (query or "").strip()
    hits: list[dict] = []
    if INDEX.exists():
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        postings = index.get("postings") or {}
        terms = [t for t in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}|[\u0600-\u06FF]{2,}", q.lower())]
        for term in terms:
            for doc in postings.get(term, [])[:12]:
                hits.append({"source": "index", "term": term, "doc": doc})
    if use_rg and q:
        rg = subprocess.run(
            ["rg", "-l", "--max-count", "20", "-g", "!node_modules", "-g", "!.git", "-g", "!.next", q, ".ai-os", "scripts/ai-os"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        for line in (rg.stdout or "").splitlines()[:20]:
            hits.append({"source": "rg", "path": line.strip()})
    rec = {
        "schema": "raios.c5-search.v1",
        "ts": utc(),
        "from": "C5",
        "query": q[:200],
        "hits": hits[:40],
        "hit_count": len(hits),
        "wal_written": False,
        "gl005_proven": False,
        "paid_api": False,
        "law": "C5_SEARCH_IS_LOCAL",
    }
    LAST_SEARCH.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return rec


def wal_untouched(fn):
    before = WAL.stat().st_mtime if WAL.exists() else None
    out = fn()
    after = WAL.stat().st_mtime if WAL.exists() else None
    if before != after:
        raise SystemExit("READ_WAL_VIOLATION")
    return out
