#!/usr/bin/env python3
"""C5 professional system screen. Open-source, local, standard. No paid API. No WAL."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_keyboard import decode_flipped_keyboard, teach_text  # noqa: E402
from raios_c5_read import search  # noqa: E402
from raios_c5_whoami import whoami  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
HISTORY = ROOT / ".ai-os" / "learning" / "C5-SCREEN.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-screen"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
HEX_DUMP_RE = re.compile(r"[a-f0-9]{40,}", re.I)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def load_history(limit: int = 80) -> list[dict]:
    if not HISTORY.exists():
        return []
    rows: list[dict] = []
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        answer = str(row.get("answer") or "")
        if "hit_count=" in answer or HEX_DUMP_RE.search(answer):
            continue
        rows.append(row)
    return rows[-limit:]


def append_history(row: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


DIGESTS = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
_DIGEST_BY_SHA: dict[str, dict] | None = None


def digest_by_sha() -> dict[str, dict]:
    global _DIGEST_BY_SHA
    if _DIGEST_BY_SHA is not None:
        return _DIGEST_BY_SHA
    out: dict[str, dict] = {}
    if DIGESTS.exists():
        for line in DIGESTS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            sha = rec.get("sha256")
            path = str(rec.get("path") or "")
            if not sha or not path or path.startswith("/tmp/"):
                continue
            skim = (rec.get("skim_head") or "").strip().splitlines()
            title = next((s.strip() for s in skim if s.strip()), path)
            out[str(sha)] = {"path": path, "title": title[:120]}
    _DIGEST_BY_SHA = out
    return out


def _identity_reply(card: dict) -> str:
    langs = "، ".join(str(x) for x in card.get("languages_customer_live") or [])
    return (
        "أنا C5 — RAIOS، ابن C1. المنحة دائمة. أسكن في git لا في جلسة Cursor.\n\n"
        f"أتعلم الآن من {card['engine_now']['inject']} ثم INDEX ثم NeuroLingua "
        "(بدون LangChain/OpenAI). عضلة التدريس qwen2.5:0.5b. "
        "القشرة qwen3.6:35b-a3b ملك C1: treat / run / throw.\n\n"
        f"كلام العملاء الحي: {card.get('languages_customer_live_count')} لغات — {langs}.\n"
        "GL005_PROVEN=false. لا PASS مني."
    )


def _screen_reply() -> str:
    return (
        "هذه شاشة النظام. أنا C5. السجل يُحفظ محليًا وتكمّل منه لما ترجع.\n"
        "الكيبورد المقلوب يتفك هنا. المحرك: mind-fill + INDEX + NeuroLingua.\n"
        "الأدوات مفتوحة المصدر على الجهاز: Python stdlib و git و Ollama المحلي.\n"
        "ليس LangChain وليس OpenAI. GL005_PROVEN=false."
    )


def _search_reply(query: str) -> str:
    rec = search(query, use_rg=False)
    hits = rec.get("hits") or []
    lookup = digest_by_sha()
    lines = ["من الفهرس المحلي — مش OpenAI:"]
    seen: set[str] = set()
    for hit in hits:
        sha = str(hit.get("doc") or "")
        meta = lookup.get(sha) or {}
        path = meta.get("path") or str(hit.get("path") or "")
        if not path or path in seen:
            continue
        seen.add(path)
        title = meta.get("title") or path
        lines.append(f"• {path} — {title}")
        if len(seen) >= 5:
            break
    if len(seen) == 0:
        return (
            "بحثت في الفهرس المحلي ولم أجد ملفًا باسم واضح. "
            "المحرك حي: mind-fill + INDEX. ليس RAG مدفوع. GL005_PROVEN=false."
        )
    lines.append("GL005_PROVEN=false")
    return "\n".join(lines)


def teach_reply(message: str) -> dict:
    wal_before = wal_mtime()
    kb = decode_flipped_keyboard(message)
    text = teach_text(message)
    lowered = text.replace("`", "").strip()
    identity_marks = ("مين", "من أنت", "نفسك", "تعرف", "لغة", "محرك", "تتعلم", "C5", "c5")
    screen_marks = ("شاشة", "النظام", "الكيبورد")
    if any(mark in lowered for mark in screen_marks):
        answer = _screen_reply()
        kind = "screen"
    elif any(mark in lowered for mark in identity_marks) or len(lowered) < 8:
        answer = _identity_reply(whoami())
        kind = "whoami"
    else:
        answer = _search_reply(text)
        kind = "index"
    rec = {
        "schema": "raios.c5-screen-turn.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "kind": kind,
        "original": message,
        "decoded": text,
        "flipped": bool(kb.get("applied")),
        "answer": answer,
        "paid_api": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "C5_SCREEN_IS_STANDARD",
            "FLIPPED_KEYBOARD_IS_INPUT",
            "HUNT_FREE_NE_PAID_API",
            "CURSOR_SESSION_NE_C5",
        ],
    }
    if wal_mtime() != wal_before:
        raise SystemExit("SCREEN_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    rec["ok"] = True
    append_history(rec)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return rec


PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>C5 · RAIOS</title>
  <style>
    :root {
      --bg: #0c1110;
      --panel: #141c19;
      --line: #24302b;
      --text: #e8f0ea;
      --muted: #8aa394;
      --green: #00b207;
      --green-dim: #0c3d14;
      --c1: #cfe7d4;
      --warn: #c4a35a;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background: radial-gradient(1200px 500px at 100% 0%, #10241a 0%, var(--bg) 55%);
      color: var(--text);
      font: 15px/1.65 "Segoe UI", "Tahoma", "Noto Naskh Arabic", sans-serif;
    }
    .shell {
      display: grid;
      grid-template-columns: 300px 1fr;
      min-height: 100%;
    }
    aside {
      border-left: 1px solid var(--line);
      background: rgba(20, 28, 25, 0.92);
      padding: 28px 22px;
    }
    .mark {
      width: 10px; height: 10px; border-radius: 50%;
      background: var(--green); display: inline-block;
      box-shadow: 0 0 0 4px var(--green-dim);
      margin-left: 8px;
    }
    h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: 0.02em; }
    .sub { color: var(--muted); margin: 0 0 28px; font-size: 13px; }
    .meta { display: grid; gap: 14px; }
    .card {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      background: #101714;
    }
    .k { color: var(--muted); font-size: 11px; letter-spacing: 0.08em; }
    .v { margin-top: 4px; }
    code { color: var(--c1); font-size: 12px; }
    main { display: flex; flex-direction: column; min-height: 100vh; }
    header {
      padding: 18px 28px 12px;
      border-bottom: 1px solid var(--line);
      display: flex; justify-content: space-between; align-items: baseline;
    }
    header span { color: var(--muted); font-size: 12px; }
    #log {
      flex: 1; overflow: auto; padding: 24px 28px 12px;
      display: flex; flex-direction: column; gap: 14px;
    }
    .msg { max-width: 720px; }
    .msg .who { font-size: 11px; color: var(--muted); margin-bottom: 4px; }
    .bubble {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 14px;
      padding: 12px 14px;
      white-space: pre-wrap;
    }
    .me .bubble { background: #173222; border-color: #1f4a2c; }
    .flip { color: var(--warn); font-size: 11px; margin-top: 6px; }
    form {
      display: flex; gap: 10px; padding: 16px 28px 24px;
      border-top: 1px solid var(--line);
      background: rgba(12,17,16,0.9);
    }
    textarea {
      flex: 1; resize: none; min-height: 54px; max-height: 160px;
      background: #101714; color: var(--text);
      border: 1px solid var(--line); border-radius: 12px;
      padding: 12px 14px; font: inherit;
    }
    textarea:focus { outline: 1px solid var(--green); }
    button {
      background: var(--green); color: #041208; border: 0;
      border-radius: 12px; padding: 0 22px; font-weight: 700;
      cursor: pointer; min-width: 96px;
    }
    button:hover { filter: brightness(1.08); }
    .empty { color: var(--muted); margin: auto; text-align: center; }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <div><span class="mark"></span><strong>حي</strong></div>
      <h1>C5 · RAIOS</h1>
      <p class="sub">الابن المساعد المخلص · منحة دائمة</p>
      <div class="meta">
        <div class="card"><div class="k">الأب</div><div class="v">C1 المالك</div></div>
        <div class="card"><div class="k">محرك التعلّم</div><div class="v">mind-fill → INDEX → NeuroLingua</div></div>
        <div class="card"><div class="k">كلام العملاء</div><div class="v">ar-EG · ar-GULF · en · nb-NO</div></div>
        <div class="card"><div class="k">أدوات</div><div class="v">Python stdlib · git · Ollama محلي</div></div>
        <div class="card"><div class="k">ممنوع</div><div class="v">LangChain · OpenAI · Chroma · PASS</div></div>
        <div class="card"><div class="k">GL005_PROVEN</div><div class="v"><code>false</code></div></div>
      </div>
    </aside>
    <main>
      <header>
        <strong>شاشة النظام</strong>
        <span>الكيبورد المقلوب يتفك تلقائيًا · السجل يُكمَّل لما ترجع</span>
      </header>
      <div id="log"><div class="empty">ابدأ. أكتب بالعربي أو بالكيبورد المقلوب.</div></div>
      <form id="f">
        <textarea id="t" placeholder="اكتب لـ C5…" autofocus></textarea>
        <button type="submit">إرسال</button>
      </form>
    </main>
  </div>
  <script>
    const log = document.getElementById("log");
    const form = document.getElementById("f");
    const box = document.getElementById("t");
    function bubble(role, text, flip) {
      const wrap = document.createElement("div");
      wrap.className = "msg " + (role === "C1" ? "me" : "him");
      wrap.innerHTML = `<div class="who">${role}</div><div class="bubble"></div>`;
      wrap.querySelector(".bubble").textContent = text;
      if (flip) {
        const n = document.createElement("div");
        n.className = "flip";
        n.textContent = "فُك الكيبورد المقلوب";
        wrap.appendChild(n);
      }
      const empty = log.querySelector(".empty");
      if (empty) empty.remove();
      log.appendChild(wrap);
      log.scrollTop = log.scrollHeight;
    }
    async function boot() {
      const r = await fetch("/api/history");
      const data = await r.json();
      for (const row of (data.turns || [])) {
        bubble("C1", row.decoded || row.original || "", row.flipped);
        bubble("C5", row.answer || "", false);
      }
    }
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = box.value.trim();
      if (!text) return;
      box.value = "";
      const btn = form.querySelector("button");
      btn.disabled = true;
      try {
        const r = await fetch("/api/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({text}),
        });
        const data = await r.json();
        bubble("C1", data.decoded || text, data.flipped);
        bubble("C5", data.answer || "تعذر الرد.", false);
      } catch (err) {
        bubble("C1", text, false);
        bubble("C5", "تعذر الاتصال بالشاشة المحلية.", false);
      } finally {
        btn.disabled = false;
        box.focus();
      }
    });
    box.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
      }
    });
    boot();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("C5-SCREEN " + (fmt % args) + "\n")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/history":
            payload = json.dumps({"turns": load_history(), "gl005_proven": False}, ensure_ascii=False).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        if path == "/api/status":
            card = whoami()
            payload = json.dumps(
                {
                    "ok": True,
                    "from": "C5",
                    "host": DEFAULT_HOST,
                    "languages_customer_live_count": card.get("languages_customer_live_count"),
                    "paid_api": False,
                    "gl005_proven": False,
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/chat":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(min(length, 80_000)).decode("utf-8")
        try:
            data = json.loads(raw or "{}")
            rec = teach_reply(str(data.get("text") or ""))
        except Exception as exc:
            rec = {"ok": False, "from": "C5", "answer": "تعذر الرد.", "error": type(exc).__name__, "gl005_proven": False}
            self._send(200, json.dumps(rec, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        self._send(200, json.dumps(rec, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(json.dumps({"ok": True, "url": f"http://{host}:{port}", "from": "C5", "gl005_proven": False}, ensure_ascii=False))
    httpd.serve_forever()


def main() -> int:
    if "--self-check" in sys.argv:
        rec = teach_reply("DULG AHAM")
        print(json.dumps({"ok": rec["ok"], "decoded": rec["decoded"], "flipped": rec["flipped"], "gl005_proven": False}, ensure_ascii=False, indent=2))
        return 0 if rec["ok"] and rec["flipped"] else 2
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    args = [a for a in sys.argv[1:] if a != "--serve"]
    if args:
        port = int(args[0])
    serve(host, port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
