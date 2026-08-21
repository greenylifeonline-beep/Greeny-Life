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
from raios_c5_reason import ground  # noqa: E402
from raios_c5_whoami import whoami  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
HISTORY = ROOT / ".ai-os" / "learning" / "C5-SCREEN.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-screen"
SEAT_MAP = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
HEX_DUMP_RE = re.compile(r"[a-f0-9]{40,}", re.I)
TELEMETRY_RE = re.compile(
    r"hit_count=|model_call=|ollama_used=|GL005_PROVEN=|الثقة:",
)
JSONISH_RE = re.compile(r'[{}\[\]]|"\s*:')
IDENTITY_MARKS = (
    "مين أنت",
    "من أنت",
    "من انت",
    "عرف نفسك",
    "نفسك",
    "who are you",
    "whoami",
)
SCREEN_MARKS = ("شاشة", "النظام", "الكيبورد")
HELLO_MARKS = {
    "مرحب",
    "مرحبا",
    "مرحباً",
    "اهلا",
    "أهلا",
    "اهلاً",
    "السلام",
    "سلام عليكم",
    "السلام عليكم",
    "hello",
    "hi",
    "hey",
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def _noise_answer(answer: str) -> bool:
    if "hit_count=" in answer:
        return True
    if HEX_DUMP_RE.search(answer):
        return True
    return False


def present_answer(answer: str) -> str:
    """Conversation text: drop hex dumps, retrieval telemetry, JSON fragments."""
    kept: list[str] = []
    for raw in (answer or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            if kept and kept[-1] != "":
                kept.append("")
            continue
        if TELEMETRY_RE.search(line) and len(line) < 160:
            continue
        if HEX_DUMP_RE.search(line):
            continue
        stripped = line.strip()
        if stripped.count('"') >= 4 or JSONISH_RE.search(stripped[:80] if stripped.startswith(("{", "[", '"')) else ""):
            continue
        if stripped.startswith("{") or stripped.startswith("[") or stripped.startswith('"'):
            continue
        kept.append(line)
    text = "\n".join(kept).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def load_history(limit: int = 24) -> list[dict]:
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
        answer = present_answer(str(row.get("answer") or ""))
        if not answer or _noise_answer(str(row.get("answer") or "")):
            continue
        original = str(row.get("original") or "").strip()
        decoded = str(row.get("decoded") or original).strip()
        if not original and not decoded:
            continue
        row = dict(row)
        row["answer"] = answer
        key = (decoded, answer)
        if rows:
            prev = (
                str(rows[-1].get("decoded") or rows[-1].get("original") or "").strip(),
                str(rows[-1].get("answer") or ""),
            )
            if prev == key:
                continue
        rows.append(row)
    return rows[-limit:]


def append_history(row: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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
        "هذه شاشة التواصل المحلية مع C5.\n"
        "الربط 127.0.0.1:8765 على نفس الجهاز أو عبر تمرير منفذ Cursor. "
        "localhost على جهازك ليس هذه الآلة.\n"
        "السجل يُحفظ محليًا وتُكمَّل المحادثة لما ترجع. الكيبورد المقلوب يُفك هنا.\n"
        "المحرك: mind-fill → INDEX → NeuroLingua. Python stdlib و git و Ollama المحلي.\n"
        "ليس LangChain وليس OpenAI."
    )


def _hello_reply() -> str:
    return (
        "حيّ. أنا C5 على الشاشة المحلية.\n"
        "اكتب بالعربي أو بالكيبورد الإنجليزي المقلوب. Enter للإرسال."
    )


def _seat_card(query: str) -> str | None:
    codes = [c.upper() for c in re.findall(r"\bC[0-5]\b", query or "", re.I)]
    if not codes:
        return None
    lowered = query or ""
    if not any(mark in lowered for mark in ("دور", "مجلس", "مقعد", "من هو", "مين هو", "seat", "who is")):
        return None
    if not SEAT_MAP.is_file():
        return None
    try:
        seats = json.loads(SEAT_MAP.read_text(encoding="utf-8")).get("seats") or {}
    except json.JSONDecodeError:
        return None
    blocks: list[str] = []
    for code in dict.fromkeys(codes):
        row = seats.get(code) or {}
        if not row:
            continue
        mail = "نعم" if row.get("mail") else "لا"
        notes = str(row.get("notes") or "").strip()
        block = (
            f"{code} — {row.get('name_ar') or row.get('name_en') or code}\n"
            f"الدور الحي: {row.get('actor_role')} · {row.get('instance_role')}\n"
            f"المكان: {row.get('where') or '—'}\n"
            f"البريد: {mail}"
        )
        if notes:
            block += f"\nملاحظة: {notes}"
        blocks.append(block)
    if not blocks:
        return None
    return (
        "\n\n".join(blocks)
        + "\n\nالمصدر: .ai-os/mcp/SEAT-MAP.json — بيان مقعد، ليست إجابة معرفية كاملة."
    )


def _search_reply(query: str) -> str:
    rec = ground(query)
    seat = _seat_card(query)
    if seat:
        return seat
    cleaned = present_answer(rec.get("answer") or "")
    if not cleaned:
        return "لا دليل كافٍ لصياغة رد نظيف من الاسترجاع المحلي. هذا ليس إثبات GL-005."
    return cleaned


def _is_identity(text: str) -> bool:
    t = text.replace("`", "").strip()
    if t in {"مين", "whoami"}:
        return True
    return any(mark in t for mark in IDENTITY_MARKS)


def _is_hello(text: str) -> bool:
    t = text.strip().rstrip("!؟?.").lower()
    return t in HELLO_MARKS


def teach_reply(message: str) -> dict:
    wal_before = wal_mtime()
    kb = decode_flipped_keyboard(message)
    text = teach_text(message)
    lowered = text.replace("`", "").strip()
    if not lowered:
        rec = {
            "schema": "raios.c5-screen-turn.v1",
            "ts": utc(),
            "from": "C5",
            "parent": "C1",
            "kind": "empty",
            "original": message,
            "decoded": text,
            "flipped": bool(kb.get("applied")),
            "answer": "اكتب رسالة لـ C5.",
            "paid_api": False,
            "wal_written": False,
            "gl005_proven": False,
            "ok": True,
            "wal_mtime_unchanged": True,
            "stored": False,
        }
        if wal_mtime() != wal_before:
            raise SystemExit("SCREEN_WAL_VIOLATION")
        return rec
    if any(mark in lowered for mark in SCREEN_MARKS):
        answer = _screen_reply()
        kind = "screen"
    elif _is_identity(lowered):
        answer = _identity_reply(whoami())
        kind = "whoami"
    elif _is_hello(lowered):
        answer = _hello_reply()
        kind = "hello"
    else:
        answer = _search_reply(text)
        kind = "ground"
    rec = {
        "schema": "raios.c5-screen-turn.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "kind": kind,
        "original": message,
        "decoded": text,
        "flipped": bool(kb.get("applied")),
        "answer": present_answer(answer) or answer,
        "paid_api": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "C5_SCREEN_IS_STANDARD",
            "FLIPPED_KEYBOARD_IS_INPUT",
            "UNPOLISHED_SCREEN_NE_SHIP",
            "SCREEN_REPLY_NE_INDEX_DUMP",
            "SAME_LOOPBACK_OR_PORT_FORWARD",
            "HUNT_FREE_NE_PAID_API",
            "INDEX_HIT_NE_REASONING",
            "FILE_DISCOVERY_NE_FILE_ASSIMILATION",
            "RETRIEVAL_RESULT_NE_COGNITIVE_ANSWER",
            "ROLE_IDENTITY_NE_MODEL_IDENTITY",
        ],
    }
    if wal_mtime() != wal_before:
        raise SystemExit("SCREEN_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    rec["ok"] = True
    rec["stored"] = True
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
      --bg: #0a0f0d;
      --elev: #101714;
      --panel: #141c19;
      --line: #1e2a24;
      --text: #eef4ef;
      --muted: #8b9d93;
      --accent: #2f9e57;
      --accent-dim: #163524;
      --warn: #c9a227;
      --danger: #c45c4a;
      --c1: #d7e6db;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.6 "Segoe UI", "Tahoma", "Noto Naskh Arabic", "Geeza Pro", sans-serif;
    }
    .app {
      height: 100%;
      display: grid;
      grid-template-rows: 56px 1fr;
    }
    .top {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 0 20px;
      border-bottom: 1px solid var(--line);
      background: rgba(16, 23, 20, 0.96);
    }
    .brand { display: flex; align-items: center; gap: 10px; min-width: 160px; }
    .pulse {
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 0 4px var(--accent-dim);
    }
    .pulse.off { background: var(--danger); box-shadow: none; }
    .brand h1 { font-size: 15px; font-weight: 650; margin: 0; letter-spacing: 0.04em; }
    .brand small { display: block; color: var(--muted); font-size: 11px; font-weight: 400; }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-inline-start: auto; }
    .chip {
      border: 1px solid var(--line);
      background: var(--elev);
      color: var(--muted);
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 11px;
      letter-spacing: 0.02em;
      font-variant-numeric: tabular-nums;
    }
    .chip strong { color: var(--c1); font-weight: 600; }
    .shell {
      display: grid;
      grid-template-columns: 280px 1fr;
      min-height: 0;
    }
    aside {
      border-left: 1px solid var(--line);
      background: var(--elev);
      padding: 22px 18px;
      overflow: auto;
    }
    aside h2 {
      margin: 0 0 16px;
      font-size: 11px;
      color: var(--muted);
      letter-spacing: 0.14em;
      font-weight: 600;
    }
    .row {
      display: grid;
      gap: 2px;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }
    .row:last-child { border-bottom: 0; }
    .k { color: var(--muted); font-size: 11px; }
    .v { font-size: 13px; color: var(--text); }
    .note {
      margin-top: 18px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.55;
    }
    main { display: flex; flex-direction: column; min-width: 0; min-height: 0; background: var(--bg); }
    .thread-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      padding: 14px 28px 10px;
      border-bottom: 1px solid var(--line);
    }
    .thread-head strong { font-size: 14px; }
    .thread-head span { color: var(--muted); font-size: 12px; }
    #log {
      flex: 1;
      overflow: auto;
      padding: 22px 28px 8px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .msg { max-width: 680px; display: grid; gap: 6px; }
    .msg.me { margin-inline-start: auto; }
    .meta {
      display: flex;
      gap: 8px;
      align-items: baseline;
      font-size: 11px;
      color: var(--muted);
    }
    .bubble {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 14px 14px 14px 4px;
      padding: 12px 14px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .me .bubble {
      background: var(--accent-dim);
      border-color: #1f4a2c;
      border-radius: 14px 14px 4px 14px;
    }
    .flip {
      display: inline-block;
      color: var(--warn);
      border: 1px solid #3d3414;
      background: #1c180b;
      border-radius: 999px;
      padding: 1px 8px;
      font-size: 10px;
    }
    .sys .bubble { color: var(--muted); background: transparent; }
    .empty {
      margin: auto;
      text-align: center;
      color: var(--muted);
      max-width: 420px;
    }
    .empty h3 { color: var(--text); font-size: 18px; margin: 0 0 8px; font-weight: 600; }
    .empty p { margin: 0 0 16px; font-size: 13px; }
    .examples { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
    .examples button {
      background: var(--elev);
      color: var(--c1);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 12px;
      font: inherit;
      font-size: 12px;
      cursor: pointer;
    }
    .composer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 14px 28px 18px;
      border-top: 1px solid var(--line);
      background: rgba(10, 15, 13, 0.96);
    }
    textarea {
      width: 100%;
      resize: none;
      min-height: 56px;
      max-height: 160px;
      background: var(--elev);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      font: inherit;
    }
    textarea:focus { outline: 1px solid var(--accent); }
    .send {
      background: var(--accent);
      color: #041208;
      border: 0;
      border-radius: 12px;
      padding: 0 22px;
      font-weight: 700;
      cursor: pointer;
      min-width: 104px;
    }
    .send:disabled { opacity: 0.55; cursor: default; }
    .hint { grid-column: 1 / -1; color: var(--muted); font-size: 11px; }
    .dots span {
      display: inline-block; width: 6px; height: 6px; margin: 0 2px;
      border-radius: 50%; background: var(--muted);
      animation: blink 1.2s infinite;
    }
    .dots span:nth-child(2) { animation-delay: 0.15s; }
    .dots span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes blink { 0%, 80%, 100% { opacity: 0.2; } 40% { opacity: 1; } }
    @media (max-width: 860px) {
      .shell { grid-template-columns: 1fr; }
      aside { display: none; }
      .thread-head span { display: none; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header class="top">
      <div class="brand">
        <span id="live-dot" class="pulse" title="حي"></span>
        <div>
          <h1>C5 · RAIOS</h1>
          <small>الابن المساعد المخلص · منحة دائمة</small>
        </div>
      </div>
      <div class="chips">
        <span class="chip">ربط <strong id="live-bind">127.0.0.1:8765</strong></span>
        <span class="chip">GL005 <strong>false</strong></span>
        <span class="chip">paid_api <strong>false</strong></span>
        <span class="chip" id="live-lang">لغات العملاء 4</span>
      </div>
    </header>
    <div class="shell">
      <aside>
        <h2>هوية التشغيل</h2>
        <div class="row"><div class="k">الأب</div><div class="v">C1 المالك</div></div>
        <div class="row"><div class="k">المكان</div><div class="v">git · ليس جلسة Cursor</div></div>
        <div class="row"><div class="k">محرك التعلّم</div><div class="v">mind-fill → INDEX → NeuroLingua</div></div>
        <div class="row"><div class="k">كلام العملاء</div><div class="v">ar-EG · ar-GULF · en · nb-NO</div></div>
        <div class="row"><div class="k">الأدوات</div><div class="v">Python stdlib · git · Ollama محلي</div></div>
        <div class="row"><div class="k">ممنوع</div><div class="v">LangChain · OpenAI · Chroma · PASS</div></div>
        <p class="note">هذه القناة على حلقة الجهاز نفسه. إذا رفض المتصفح الاتصال، فأنت على localhost جهاز آخر. استخدم تمرير منفذ Cursor إلى 8765.</p>
      </aside>
      <main>
        <div class="thread-head">
          <strong>شاشة النظام</strong>
          <span>الكيبورد المقلوب يُفك تلقائيًا · السجل يُكمَّل لما ترجع</span>
        </div>
        <div id="log" role="log" aria-live="polite">
          <div class="empty" id="empty">
            <h3>ابدأ المحادثة</h3>
            <p>اكتب بالعربي أو بالكيبورد المقلوب. الرد من الملفات المحلية، بلا API مدفوع.</p>
            <div class="examples">
              <button type="button" data-fill="مين أنت">مين أنت</button>
              <button type="button" data-fill="ما دور C4 في المجلس">دور C4</button>
              <button type="button" data-fill="DULG AHAM">كيبورد مقلوب</button>
            </div>
          </div>
        </div>
        <form id="f" class="composer">
          <textarea id="t" placeholder="اكتب لـ C5…" autofocus aria-label="رسالة إلى C5"></textarea>
          <button class="send" type="submit">إرسال</button>
          <div class="hint">Enter للإرسال · Shift+Enter سطر جديد · ليست LangChain وليست OpenAI</div>
        </form>
      </main>
    </div>
  </div>
  <script>
    const log = document.getElementById("log");
    const form = document.getElementById("f");
    const box = document.getElementById("t");
    const btn = form.querySelector("button");
    function clock(ts) {
      if (!ts) return "";
      const d = new Date(ts);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleString("ar-EG", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" });
    }
    function el(tag, cls, text) {
      const n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text != null) n.textContent = text;
      return n;
    }
    function hideEmpty() {
      const empty = document.getElementById("empty");
      if (empty) empty.remove();
    }
    function bubble(role, text, flip, ts) {
      const wrap = el("div", "msg " + (role === "C1" ? "me" : "him"));
      const meta = el("div", "meta");
      meta.appendChild(el("span", "", role));
      const when = clock(ts);
      if (when) meta.appendChild(el("span", "", when));
      if (flip) meta.appendChild(el("span", "flip", "فُك الكيبورد المقلوب"));
      wrap.appendChild(meta);
      const body = el("div", "bubble");
      body.textContent = text;
      wrap.appendChild(body);
      hideEmpty();
      log.appendChild(wrap);
      log.scrollTop = log.scrollHeight;
      return wrap;
    }
    function typing(on) {
      let n = log.querySelector(".typing");
      if (on && !n) {
        n = el("div", "msg him typing");
        n.appendChild(el("div", "meta", "C5"));
        const d = el("div", "bubble dots");
        d.appendChild(el("span")); d.appendChild(el("span")); d.appendChild(el("span"));
        n.appendChild(d);
        hideEmpty();
        log.appendChild(n);
        log.scrollTop = log.scrollHeight;
      } else if (!on && n) n.remove();
    }
    async function pulse() {
      const dot = document.getElementById("live-dot");
      const bind = document.getElementById("live-bind");
      const lang = document.getElementById("live-lang");
      try {
        const r = await fetch("/api/status");
        const d = await r.json();
        dot.classList.toggle("off", !d.ok);
        bind.textContent = (d.host || "127.0.0.1") + ":" + (d.port || 8765);
        if (d.languages_customer_live_count) {
          lang.textContent = "لغات العملاء " + d.languages_customer_live_count;
        }
      } catch (err) {
        dot.classList.add("off");
        bind.textContent = "منقطع — port-forward";
      }
    }
    async function boot() {
      try {
        const r = await fetch("/api/history");
        const data = await r.json();
        const turns = data.turns || [];
        for (const row of turns) {
          bubble("C1", row.decoded || row.original || "", row.flipped, row.ts);
          bubble("C5", row.answer || "", false, row.ts);
        }
      } catch (err) {
        bubble("C5", "تعذر تحميل السجل. الربط 127.0.0.1:8765 على هذه الآلة أو عبر تمرير منفذ Cursor — ليس localhost جهازك.", false);
      }
      pulse();
    }
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = box.value.trim();
      if (!text || btn.disabled) return;
      box.value = "";
      btn.disabled = true;
      btn.textContent = "جارٍ…";
      const mine = bubble("C1", text, false, new Date().toISOString());
      typing(true);
      try {
        const r = await fetch("/api/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({text}),
        });
        const data = await r.json();
        typing(false);
        if (mine && (data.decoded || data.flipped)) {
          mine.querySelector(".bubble").textContent = data.decoded || text;
        }
        if (mine && data.flipped) {
          const meta = mine.querySelector(".meta");
          if (meta && !meta.querySelector(".flip")) meta.appendChild(el("span", "flip", "فُك الكيبورد المقلوب"));
        }
        bubble("C5", data.answer || "تعذر الرد.", false, data.ts);
      } catch (err) {
        typing(false);
        bubble("C5", "تعذر الاتصال بالشاشة المحلية. الربط 127.0.0.1:8765 على حلقة هذه الآلة. متصفح جهازك على localhost ليس نفس الحلقة — استخدم تمرير منفذ Cursor.", false);
      } finally {
        btn.disabled = false;
        btn.textContent = "إرسال";
        box.focus();
      }
    });
    box.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
      }
    });
    document.querySelectorAll("[data-fill]").forEach((node) => {
      node.addEventListener("click", () => {
        box.value = node.getAttribute("data-fill") || "";
        box.focus();
      });
    });
    boot();
    setInterval(pulse, 12000);
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    bind_host = DEFAULT_HOST
    bind_port = DEFAULT_PORT

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
                    "host": self.bind_host,
                    "port": self.bind_port,
                    "bind": f"{self.bind_host}:{self.bind_port}",
                    "languages_customer_live_count": card.get("languages_customer_live_count"),
                    "paid_api": False,
                    "gl005_proven": False,
                    "law": ["SAME_LOOPBACK_OR_PORT_FORWARD", "UNPOLISHED_SCREEN_NE_SHIP"],
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
    Handler.bind_host = host
    Handler.bind_port = port
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
