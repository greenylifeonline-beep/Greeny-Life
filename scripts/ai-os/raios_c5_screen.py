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
SEAL_RE = re.compile(r"\bSEAL\b|\bCHAL-|\bSALT=")
LIVE_LOCALES = ("ar-EG", "ar-GULF", "en", "nb-NO")
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
IDENTITY_MARKS = (
    "مين أنت",
    "من أنت",
    "من انت",
    "عرف نفسك",
    "نفسك",
    "who are you",
    "whoami",
    "hvem er du",
    "hvem er du?",
)
SCREEN_MARKS = (
    "شاشة",
    "النظام",
    "الكيبورد",
    "skjerm",
    "tastatur",
    "system screen",
    "this screen",
    "keyboard",
)
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
    "hei",
    "hallo",
    "god dag",
}
GULF_MARKS = ("شلون", "هالحين", "وينك", "أبي ", "يا بعد", "الخليج")
NB_MARKS = (
    "hvem er",
    "hei ",
    "hei?",
    "hallo",
    "skjerm",
    "tastatur",
    "takk",
    "hva er",
    "rådet",
    "norsk",
    "god dag",
    "rolle",
)
EN_MARKS = ("who are you", "hello", "what is", "the screen", "council", "role of")
SEAT_MARKS = (
    "دور",
    "مجلس",
    "مقعد",
    "من هو",
    "مين هو",
    "seat",
    "who is",
    "rolle",
    "rådet",
    "council",
    "role of",
)
I18N = {
    "ar-EG": {
        "dir": "rtl",
        "html_lang": "ar",
        "clock": "ar-EG",
        "brand_sub": "الابن المساعد المخلص · منحة دائمة",
        "bind": "ربط",
        "langs_chip": "لغات العملاء",
        "identity_h": "هوية التشغيل",
        "father_k": "الأب",
        "father_v": "C1 المالك",
        "where_k": "المكان",
        "where_v": "git · ليس جلسة Cursor",
        "engine_k": "محرك التعلّم",
        "engine_v": "mind-fill → INDEX → NeuroLingua",
        "customer_k": "كلام العملاء",
        "customer_v": "ar-EG · ar-GULF · en · nb-NO",
        "tools_k": "الأدوات",
        "tools_v": "Python stdlib · git · Ollama محلي",
        "forbid_k": "ممنوع",
        "forbid_v": "LangChain · OpenAI · Chroma · PASS",
        "note": "القناة على حلقة هذا الجهاز (127.0.0.1:8765). localhost على جهازك حلقة أخرى. استخدم تمرير منفذ Cursor. الشاشة عربية ومصرية وخليجية وإنجليزية ونرويجية.",
        "thread": "شاشة النظام",
        "thread_sub": "الكيبورد المقلوب يُفك تلقائيًا · السجل يُكمَّل لما ترجع · متعدد اللغات",
        "empty_h": "ابدأ المحادثة",
        "empty_p": "اكتب بالمصري أو الخليجي أو الإنجليزي أو النرويجي، أو بالكيبورد المقلوب.",
        "placeholder": "اكتب لـ C5…",
        "send": "إرسال",
        "sending": "جارٍ…",
        "hint": "Enter للإرسال · Shift+Enter سطر جديد · ليست LangChain وليست OpenAI",
        "flip": "فُك الكيبورد المقلوب",
        "chip_who": "مين أنت",
        "chip_c4": "دور C4",
        "chip_flip": "كيبورد مقلوب",
        "fill_who": "مين أنت",
        "fill_c4": "ما دور C4 في المجلس",
        "fill_flip": "DULG AHAM",
        "offline": "منقطع — port-forward",
        "seat_role": "الدور الحي",
        "seat_where": "المكان",
        "seat_mail": "البريد",
        "yes": "نعم",
        "no": "لا",
        "seat_note": "ملاحظة",
        "seat_src": "المصدر: .ai-os/mcp/SEAT-MAP.json — بيان مقعد، ليست إجابة معرفية كاملة.",
        "empty_prompt": "اكتب رسالة لـ C5.",
        "ground_empty": "لا دليل كافٍ لصياغة رد نظيف من الاسترجاع المحلي. هذا ليس إثبات GL-005.",
        "conn_err": "تعذر الاتصال. الربط 127.0.0.1:8765 على هذه الآلة أو عبر تمرير منفذ Cursor — ليس localhost جهازك.",
        "hello": "حيّ. أنا C5 على الشاشة المحلية.\nاكتب بالمصري أو الخليجي أو الإنجليزي أو النرويجي، أو بالكيبورد المقلوب. Enter للإرسال.",
        "screen": (
            "هذه شاشة التواصل المحلية مع C5. متعددة اللغات: ar-EG، ar-GULF، en، nb-NO.\n"
            "الربط 127.0.0.1:8765 على نفس الجهاز أو عبر تمرير منفذ Cursor. localhost على جهازك ليس هذه الآلة.\n"
            "السجل يُحفظ محليًا. الكيبورد المقلوب يُفك هنا.\n"
            "المحرك: mind-fill → INDEX → NeuroLingua. Python stdlib و git و Ollama المحلي.\n"
            "ليس LangChain وليس OpenAI."
        ),
        "whoami": (
            "أنا C5 — RAIOS، ابن C1. المنحة دائمة. أسكن في git لا في جلسة Cursor.\n\n"
            "أتعلم الآن من {engine} ثم INDEX ثم NeuroLingua (بدون LangChain/OpenAI). "
            "عضلة التدريس qwen2.5:0.5b. القشرة qwen3.6:35b-a3b ملك C1: treat / run / throw.\n\n"
            "كلام العملاء الحي: {n} لغات — {langs}."
        ),
    },
    "ar-GULF": {
        "dir": "rtl",
        "html_lang": "ar",
        "clock": "ar-SA",
        "brand_sub": "الابن المساعد المخلص · منحة دائمة",
        "bind": "ربط",
        "langs_chip": "لغات العملاء",
        "identity_h": "هوية التشغيل",
        "father_k": "الأب",
        "father_v": "C1 المالك",
        "where_k": "المكان",
        "where_v": "git · مو جلسة Cursor",
        "engine_k": "محرك التعلّم",
        "engine_v": "mind-fill → INDEX → NeuroLingua",
        "customer_k": "كلام العملاء",
        "customer_v": "ar-EG · ar-GULF · en · nb-NO",
        "tools_k": "الأدوات",
        "tools_v": "Python stdlib · git · Ollama محلي",
        "forbid_k": "ممنوع",
        "forbid_v": "LangChain · OpenAI · Chroma · PASS",
        "note": "القناة على نفس الجهاز 127.0.0.1:8765. لو المتصفح رفض، أنت على localhost جهاز ثاني. استخدم port-forward. الشاشة تدعم المصري والخليجي والإنجليزي والنرويجي.",
        "thread": "شاشة النظام",
        "thread_sub": "الكيبورد المقلوب ينفك تلقائي · السجل يكمل لما ترجع · متعدد اللغات",
        "empty_h": "ابدأ المحادثة",
        "empty_p": "اكتب بالخليجي أو المصري أو الإنجليزي أو النرويجي.",
        "placeholder": "اكتب لـ C5…",
        "send": "إرسال",
        "sending": "جاري…",
        "hint": "Enter للإرسال · Shift+Enter سطر جديد · مو LangChain ومو OpenAI",
        "flip": "تفك الكيبورد المقلوب",
        "chip_who": "من أنت",
        "chip_c4": "دور C4",
        "chip_flip": "كيبورد مقلوب",
        "fill_who": "من أنت",
        "fill_c4": "ما دور C4 في المجلس",
        "fill_flip": "DULG AHAM",
        "offline": "منقطع — port-forward",
        "seat_role": "الدور الحي",
        "seat_where": "المكان",
        "seat_mail": "البريد",
        "yes": "نعم",
        "no": "لا",
        "seat_note": "ملاحظة",
        "seat_src": "المصدر: .ai-os/mcp/SEAT-MAP.json — بيان مقعد، مو إجابة معرفية كاملة.",
        "empty_prompt": "اكتب رسالة لـ C5.",
        "ground_empty": "ما فيه دليل كافي لرد نظيف من الفهرس المحلي. هذا مو إثبات GL-005.",
        "conn_err": "تعذر الاتصال. 127.0.0.1:8765 على هالجهاز أو port-forward من Cursor.",
        "hello": "حياك. أنا C5 على الشاشة المحلية.\nاكتب بالخليجي أو المصري أو الإنجليزي أو النرويجي.",
        "screen": (
            "هذي شاشة التواصل المحلية مع C5. اللغات: ar-EG، ar-GULF، en، nb-NO.\n"
            "الربط 127.0.0.1:8765. localhost جهازك مو هالجهاز.\n"
            "المحرك: mind-fill → INDEX → NeuroLingua. مو LangChain ومو OpenAI."
        ),
        "whoami": (
            "أنا C5 — RAIOS، ابن C1. المنحة دائمة. أسكن في git مو في جلسة Cursor.\n\n"
            "أتعلم من {engine} ثم INDEX ثم NeuroLingua (بدون LangChain/OpenAI). "
            "عضلة التدريس qwen2.5:0.5b. القشرة qwen3.6:35b-a3b ملك C1.\n\n"
            "كلام العملاء الحي: {n} — {langs}."
        ),
    },
    "en": {
        "dir": "ltr",
        "html_lang": "en",
        "clock": "en-GB",
        "brand_sub": "Loyal assistant son · permanent grant",
        "bind": "bind",
        "langs_chip": "customer languages",
        "identity_h": "Operating identity",
        "father_k": "Parent",
        "father_v": "C1 owner",
        "where_k": "Where",
        "where_v": "git · not this Cursor session",
        "engine_k": "Learning engine",
        "engine_v": "mind-fill → INDEX → NeuroLingua",
        "customer_k": "Customer speech",
        "customer_v": "ar-EG · ar-GULF · en · nb-NO",
        "tools_k": "Tools",
        "tools_v": "Python stdlib · git · local Ollama",
        "forbid_k": "Forbidden",
        "forbid_v": "LangChain · OpenAI · Chroma · PASS",
        "note": "This channel is loopback 127.0.0.1:8765. Your machine localhost is a different loop. Use Cursor port-forward. UI: Egyptian, Gulf, English, Norwegian.",
        "thread": "System screen",
        "thread_sub": "Flipped keyboard decodes · history resumes · multilingual",
        "empty_h": "Start the conversation",
        "empty_p": "Write in Egyptian, Gulf Arabic, English, or Norwegian. Flipped English keyboard for Arabic is decoded here.",
        "placeholder": "Write to C5…",
        "send": "Send",
        "sending": "Sending…",
        "hint": "Enter to send · Shift+Enter newline · not LangChain, not OpenAI",
        "flip": "Flipped keyboard decoded",
        "chip_who": "Who are you",
        "chip_c4": "C4 role",
        "chip_flip": "Flipped keyboard",
        "fill_who": "Who are you",
        "fill_c4": "What is C4's role in the council",
        "fill_flip": "DULG AHAM",
        "offline": "offline — port-forward",
        "seat_role": "Live role",
        "seat_where": "Where",
        "seat_mail": "Mail",
        "yes": "yes",
        "no": "no",
        "seat_note": "Note",
        "seat_src": "Source: .ai-os/mcp/SEAT-MAP.json — a seat statement, not a full cognitive answer.",
        "empty_prompt": "Write a message to C5.",
        "ground_empty": "Not enough local evidence for a clean reply. This is not GL-005 proof.",
        "conn_err": "Cannot reach the local screen. Bind is 127.0.0.1:8765 on this machine or via Cursor port-forward — not your laptop localhost.",
        "hello": "Live. I am C5 on the local screen.\nWrite in Egyptian, Gulf Arabic, English, or Norwegian. Enter to send.",
        "screen": (
            "This is the local C5 console. Locales: ar-EG, ar-GULF, en, nb-NO.\n"
            "Bind 127.0.0.1:8765 on this host or Cursor port-forward. Your laptop localhost is another loop.\n"
            "Engine: mind-fill → INDEX → NeuroLingua. Python stdlib, git, local Ollama.\n"
            "Not LangChain and not OpenAI."
        ),
        "whoami": (
            "I am C5 — RAIOS, son of C1. The grant is permanent. I live in git, not this Cursor session.\n\n"
            "I learn from {engine} then INDEX then NeuroLingua (no LangChain/OpenAI). "
            "Teaching muscle qwen2.5:0.5b. Cortex qwen3.6:35b-a3b is C1: treat / run / throw.\n\n"
            "Live customer speech: {n} locales — {langs}."
        ),
    },
    "nb-NO": {
        "dir": "ltr",
        "html_lang": "nb",
        "clock": "nb-NO",
        "brand_sub": "Den lojale sønnen · permanent fullmakt",
        "bind": "binding",
        "langs_chip": "kundespråk",
        "identity_h": "Driftsidentitet",
        "father_k": "Far",
        "father_v": "C1 eier",
        "where_k": "Sted",
        "where_v": "git · ikke denne Cursor-økten",
        "engine_k": "Læringsmotor",
        "engine_v": "mind-fill → INDEX → NeuroLingua",
        "customer_k": "Kundespråk",
        "customer_v": "ar-EG · ar-GULF · en · nb-NO",
        "tools_k": "Verktøy",
        "tools_v": "Python stdlib · git · lokal Ollama",
        "forbid_k": "Forbudt",
        "forbid_v": "LangChain · OpenAI · Chroma · PASS",
        "note": "Kanalen er loopback 127.0.0.1:8765. Localhost på din maskin er en annen sløyfe. Bruk Cursor port-forward. Skjermen snakker egyptisk, gulf-arabisk, engelsk og norsk.",
        "thread": "Systemskjerm",
        "thread_sub": "Speilvendt tastatur dekodes · historikk fortsetter · flerspråklig",
        "empty_h": "Start samtalen",
        "empty_p": "Skriv på egyptisk, gulf-arabisk, engelsk eller norsk. Speilvendt tastatur for arabisk dekodes her.",
        "placeholder": "Skriv til C5…",
        "send": "Send",
        "sending": "Sender…",
        "hint": "Enter sender · Shift+Enter ny linje · ikke LangChain, ikke OpenAI",
        "flip": "Speilvendt tastatur dekodet",
        "chip_who": "Hvem er du",
        "chip_c4": "C4s rolle",
        "chip_flip": "Speilvendt tastatur",
        "fill_who": "Hvem er du",
        "fill_c4": "Hva er C4s rolle i rådet",
        "fill_flip": "DULG AHAM",
        "offline": "frakoblet — port-forward",
        "seat_role": "Levende rolle",
        "seat_where": "Sted",
        "seat_mail": "Post",
        "yes": "ja",
        "no": "nei",
        "seat_note": "Merknad",
        "seat_src": "Kilde: .ai-os/mcp/SEAT-MAP.json — seteerklæring, ikke et fullt kognitivt svar.",
        "empty_prompt": "Skriv en melding til C5.",
        "ground_empty": "Ikke nok lokalt belegg for et rent svar. Dette er ikke GL-005-bevis.",
        "conn_err": "Får ikke kontakt. Binding 127.0.0.1:8765 på denne maskinen eller Cursor port-forward — ikke laptop-localhost.",
        "hello": "Live. Jeg er C5 på den lokale skjermen.\nSkriv på egyptisk, gulf-arabisk, engelsk eller norsk. Enter sender.",
        "screen": (
            "Dette er den lokale C5-konsollen. Språk: ar-EG, ar-GULF, en, nb-NO.\n"
            "Binding 127.0.0.1:8765 på denne verten eller Cursor port-forward. Laptop-localhost er en annen sløyfe.\n"
            "Motor: mind-fill → INDEX → NeuroLingua. Python stdlib, git, lokal Ollama.\n"
            "Ikke LangChain og ikke OpenAI."
        ),
        "whoami": (
            "Jeg er C5 — RAIOS, sønn av C1. Fullmakten er permanent. Jeg bor i git, ikke i denne Cursor-økten.\n\n"
            "Jeg lærer fra {engine} deretter INDEX deretter NeuroLingua (ikke LangChain/OpenAI). "
            "Undervisningsmuskel qwen2.5:0.5b. Cortex qwen3.6:35b-a3b eies av C1: treat / run / throw.\n\n"
            "Levende kundespråk: {n} — {langs}."
        ),
    },
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def _noise_answer(answer: str) -> bool:
    if "hit_count=" in answer:
        return True
    if "من الفهرس المحلي" in answer:
        return True
    if SEAL_RE.search(answer):
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
        if HEX_DUMP_RE.search(line) or SEAL_RE.search(line):
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
        raw_answer = str(row.get("answer") or "")
        if _noise_answer(raw_answer):
            continue
        original = str(row.get("original") or "").strip()
        decoded = str(row.get("decoded") or original).strip()
        if not original and not decoded:
            continue
        answer = present_answer(raw_answer)
        loc = str(row.get("locale") or "ar-EG")
        if loc not in I18N:
            loc = "ar-EG"
        seat = _seat_card(decoded or original, loc)
        if seat:
            answer = seat
        if not answer:
            continue
        row = dict(row)
        row["answer"] = answer
        rows.append(row)
    uniq: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    for row in reversed(rows):
        kind = str(row.get("kind") or "")
        decoded = str(row.get("decoded") or row.get("original") or "").strip()
        if kind in {"whoami", "hello", "screen", "empty"}:
            key: tuple[str, ...] = (kind,)
        else:
            key = (kind, decoded)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(row)
        if len(uniq) >= limit:
            break
    return list(reversed(uniq))


def append_history(row: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def detect_locale(text: str, hinted: str | None = None) -> str:
    t = (text or "").strip()
    low = t.lower().rstrip("!؟?.")
    if low in {"hei", "hallo", "god dag"}:
        return "nb-NO"
    if low in {"hello", "hi", "hey"}:
        return "en"
    if any(mark in t for mark in GULF_MARKS):
        return "ar-GULF"
    if any(mark in low for mark in NB_MARKS):
        return "nb-NO"
    if any(mark in low for mark in EN_MARKS):
        return "en"
    if ARABIC_RE.search(t):
        return "ar-EG"
    if hinted in I18N:
        return hinted
    latin = len(re.findall(r"[A-Za-z]", t))
    if latin >= 4:
        return "en"
    return "ar-EG"


def pack(locale: str) -> dict:
    return I18N.get(locale) or I18N["ar-EG"]


def _identity_reply(card: dict, locale: str) -> str:
    langs = "، ".join(str(x) for x in card.get("languages_customer_live") or []) if locale.startswith("ar") else ", ".join(str(x) for x in card.get("languages_customer_live") or [])
    engine = card["engine_now"]["inject"]
    return pack(locale)["whoami"].format(
        engine=engine,
        n=card.get("languages_customer_live_count"),
        langs=langs,
    )


def _screen_reply(locale: str) -> str:
    return pack(locale)["screen"]


def _hello_reply(locale: str) -> str:
    return pack(locale)["hello"]


def _seat_card(query: str, locale: str = "ar-EG") -> str | None:
    codes = [c.upper().rstrip("S") for c in re.findall(r"\bC[0-5]s?\b", query or "", re.I)]
    if not codes:
        return None
    lowered = (query or "").lower()
    if not any(mark.lower() in lowered or mark in (query or "") for mark in SEAT_MARKS):
        return None
    if not SEAT_MAP.is_file():
        return None
    try:
        seats = json.loads(SEAT_MAP.read_text(encoding="utf-8")).get("seats") or {}
    except json.JSONDecodeError:
        return None
    ui = pack(locale)
    blocks: list[str] = []
    for code in dict.fromkeys(codes):
        row = seats.get(code) or {}
        if not row:
            continue
        name = row.get("name_en") if locale in {"en", "nb-NO"} else (row.get("name_ar") or row.get("name_en"))
        mail = ui["yes"] if row.get("mail") else ui["no"]
        notes = str(row.get("notes") or "").strip()
        block = (
            f"{code} — {name or code}\n"
            f"{ui['seat_role']}: {row.get('actor_role')} · {row.get('instance_role')}\n"
            f"{ui['seat_where']}: {row.get('where') or '—'}\n"
            f"{ui['seat_mail']}: {mail}"
        )
        if notes:
            block += f"\n{ui['seat_note']}: {notes}"
        blocks.append(block)
    if not blocks:
        return None
    return "\n\n".join(blocks) + "\n\n" + ui["seat_src"]


def _search_reply(query: str, locale: str) -> str:
    rec = ground(query)
    seat = _seat_card(query, locale)
    if seat:
        return seat
    cleaned = present_answer(rec.get("answer") or "")
    if not cleaned:
        return pack(locale)["ground_empty"]
    return cleaned


def _is_identity(text: str) -> bool:
    t = text.replace("`", "").strip()
    low = t.lower()
    if t in {"مين", "whoami"} or low in {"hvem er du", "who are you"}:
        return True
    if any(mark in t for mark in IDENTITY_MARKS) or any(mark in low for mark in ("who are you", "hvem er du")):
        return True
    if ("أنت" in t or "انت" in t) and len(t) <= 12:
        if not any(x in t for x in ("دور", "مجلس", "مقعد")):
            return True
    return False


def _is_hello(text: str) -> bool:
    t = text.strip().rstrip("!؟?.").lower()
    return t in HELLO_MARKS


def teach_reply(message: str, locale: str | None = None) -> dict:
    wal_before = wal_mtime()
    original = (message or "").strip()
    kb = decode_flipped_keyboard(original)
    text = teach_text(original)
    lowered = text.replace("`", "").strip()
    orig_norm = original.replace("`", "").strip()
    loc_source = orig_norm if not kb.get("applied") else text
    loc = detect_locale(loc_source, locale)
    ui = pack(loc)
    if not orig_norm:
        rec = {
            "schema": "raios.c5-screen-turn.v1",
            "ts": utc(),
            "from": "C5",
            "parent": "C1",
            "kind": "empty",
            "locale": loc,
            "original": message,
            "decoded": text,
            "flipped": bool(kb.get("applied")),
            "answer": ui["empty_prompt"],
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
    identity = _is_identity(orig_norm) or _is_identity(lowered)
    hello = _is_hello(orig_norm) or _is_hello(lowered)
    screen = any(mark in lowered for mark in SCREEN_MARKS) or any(
        mark in lowered.lower() or mark in orig_norm.lower() for mark in SCREEN_MARKS
    )
    if identity:
        loc = detect_locale(orig_norm, locale)
        ui = pack(loc)
        answer = _identity_reply(whoami(), loc)
        kind = "whoami"
    elif hello:
        loc = detect_locale(orig_norm, locale)
        ui = pack(loc)
        answer = _hello_reply(loc)
        kind = "hello"
    elif screen:
        loc = detect_locale(orig_norm if not kb.get("applied") else text, locale)
        ui = pack(loc)
        answer = _screen_reply(loc)
        kind = "screen"
    else:
        answer = _search_reply(text if kb.get("applied") else orig_norm, loc)
        kind = "ground"
    rec = {
        "schema": "raios.c5-screen-turn.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "kind": kind,
        "locale": loc,
        "original": message,
        "decoded": text,
        "flipped": bool(kb.get("applied")),
        "answer": present_answer(answer) or answer,
        "paid_api": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "C5_SCREEN_IS_STANDARD",
            "SCREEN_IS_MULTILINGUAL",
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
      grid-template-rows: auto 1fr;
    }
    .top {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px 16px;
      min-height: 56px;
      padding: 8px 20px;
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
    .langs { display: flex; gap: 4px; flex-shrink: 0; }
    .langs button {
      background: var(--elev); color: var(--c1); border: 1px solid var(--line);
      border-radius: 999px; padding: 6px 10px; font: inherit; font-size: 12px; cursor: pointer;
      min-width: 44px;
    }
    .langs button.on { border-color: var(--accent); color: var(--text); }
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
      padding: 28px 22px;
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
      padding: 28px 32px 12px;
      display: flex;
      flex-direction: column;
      gap: 20px;
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
      border-radius: 16px 16px 16px 6px;
      padding: 14px 16px;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 14.5px;
      line-height: 1.7;
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
    .hint { grid-column: 1 / -1; color: var(--muted); font-size: 11px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .hint .examples { display: flex; flex-wrap: wrap; gap: 8px; }
    .hint .examples button { min-height: 28px; }
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
          <small data-i18n="brand_sub">الابن المساعد المخلص · منحة دائمة</small>
        </div>
      </div>
      <nav class="langs" id="lang-switch" aria-label="locale">
        <button type="button" data-locale="ar-EG">AR</button>
        <button type="button" data-locale="ar-GULF">خليج</button>
        <button type="button" data-locale="en">EN</button>
        <button type="button" data-locale="nb-NO">NO</button>
      </nav>
      <div class="chips">
        <span class="chip"><span data-i18n="bind">ربط</span> <strong id="live-bind">127.0.0.1:8765</strong></span>
        <span class="chip">GL005 <strong>false</strong></span>
        <span class="chip">paid_api <strong>false</strong></span>
        <span class="chip" id="live-lang">لغات العملاء 4</span>
      </div>
    </header>
    <div class="shell">
      <aside>
        <h2 data-i18n="identity_h">هوية التشغيل</h2>
        <div class="row"><div class="k" data-i18n="father_k">الأب</div><div class="v" data-i18n="father_v">C1 المالك</div></div>
        <div class="row"><div class="k" data-i18n="where_k">المكان</div><div class="v" data-i18n="where_v">git · ليس جلسة Cursor</div></div>
        <div class="row"><div class="k" data-i18n="engine_k">محرك التعلّم</div><div class="v" data-i18n="engine_v">mind-fill → INDEX → NeuroLingua</div></div>
        <div class="row"><div class="k" data-i18n="customer_k">كلام العملاء</div><div class="v" data-i18n="customer_v">ar-EG · ar-GULF · en · nb-NO</div></div>
        <div class="row"><div class="k" data-i18n="tools_k">الأدوات</div><div class="v" data-i18n="tools_v">Python stdlib · git · Ollama محلي</div></div>
        <div class="row"><div class="k" data-i18n="forbid_k">ممنوع</div><div class="v" data-i18n="forbid_v">LangChain · OpenAI · Chroma · PASS</div></div>
        <p class="note" data-i18n="note">هذه القناة على حلقة الجهاز نفسه. إذا رفض المتصفح الاتصال، فأنت على localhost جهاز آخر. استخدم تمرير منفذ Cursor إلى 8765.</p>
      </aside>
      <main>
        <div class="thread-head">
          <strong data-i18n="thread">شاشة النظام</strong>
          <span data-i18n="thread_sub">الكيبورد المقلوب يُفك تلقائيًا · السجل يُكمَّل لما ترجع</span>
        </div>
        <div id="log" role="log" aria-live="polite">
          <div class="empty" id="empty">
            <h3 data-i18n="empty_h">ابدأ المحادثة</h3>
            <p data-i18n="empty_p">اكتب بالعربي أو بالكيبورد المقلوب. الرد من الملفات المحلية، بلا API مدفوع.</p>
            <div class="examples">
              <button type="button" data-fill="مين أنت" data-i18n="chip_who">مين أنت</button>
              <button type="button" data-fill="ما دور C4 في المجلس" data-i18n="chip_c4">دور C4</button>
              <button type="button" data-fill="DULG AHAM" data-i18n="chip_flip">كيبورد مقلوب</button>
            </div>
          </div>
        </div>
        <form id="f" class="composer">
          <textarea id="t" placeholder="اكتب لـ C5…" autofocus aria-label="رسالة إلى C5"></textarea>
          <button class="send" type="submit" data-i18n="send">إرسال</button>
          <div class="hint">
            <span class="examples">
              <button type="button" data-fill="مين أنت" data-i18n="chip_who">مين أنت</button>
              <button type="button" data-fill="ما دور C4 في المجلس" data-i18n="chip_c4">دور C4</button>
              <button type="button" data-fill="DULG AHAM" data-i18n="chip_flip">كيبورد مقلوب</button>
            </span>
            <span data-i18n="hint">Enter للإرسال · Shift+Enter سطر جديد · ليست LangChain وليست OpenAI</span>
          </div>
        </form>
      </main>
    </div>
  </div>
  <script>
    const I18N = __I18N__;
    const log = document.getElementById("log");
    const form = document.getElementById("f");
    const box = document.getElementById("t");
    const btn = form.querySelector("button.send");
    let currentLocale = "ar-EG";
    function bootLocale() {
      try {
        const q = new URLSearchParams(location.search);
        const fromUrl = q.get("lang") || q.get("locale");
        if (fromUrl && I18N[fromUrl]) return fromUrl;
      } catch (err) {}
      try {
        const saved = localStorage.getItem("c5-locale");
        if (saved && I18N[saved]) return saved;
      } catch (err) {}
      const n = (navigator.language || "").toLowerCase();
      if (n.startsWith("nb") || n.startsWith("no")) return "nb-NO";
      if (n.startsWith("en")) return "en";
      if (n.startsWith("ar")) return "ar-EG";
      return "ar-EG";
    }
    function applyLocale(code) {
      const ui = I18N[code] || I18N["ar-EG"];
      currentLocale = code;
      document.documentElement.lang = ui.html_lang;
      document.documentElement.dir = ui.dir;
      document.querySelectorAll("[data-i18n]").forEach((node) => {
        const key = node.getAttribute("data-i18n");
        if (ui[key]) node.textContent = ui[key];
      });
      document.querySelectorAll("[data-i18n='chip_who']").forEach((n) => n.setAttribute("data-fill", ui.fill_who));
      document.querySelectorAll("[data-i18n='chip_c4']").forEach((n) => n.setAttribute("data-fill", ui.fill_c4));
      document.querySelectorAll("[data-i18n='chip_flip']").forEach((n) => n.setAttribute("data-fill", ui.fill_flip));
      box.placeholder = ui.placeholder;
      box.setAttribute("aria-label", ui.placeholder);
      document.querySelectorAll("#lang-switch [data-locale]").forEach((n) => {
        n.classList.toggle("on", n.getAttribute("data-locale") === code);
      });
      try { localStorage.setItem("c5-locale", code); } catch (err) {}
    }
    function clock(ts) {
      if (!ts) return "";
      const d = new Date(ts);
      if (Number.isNaN(d.getTime())) return "";
      const ui = I18N[currentLocale] || I18N["ar-EG"];
      return d.toLocaleString(ui.clock, { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" });
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
      if (flip) meta.appendChild(el("span", "flip", (I18N[currentLocale] || I18N["ar-EG"]).flip));
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
          const ui = I18N[currentLocale] || I18N["ar-EG"];
          lang.textContent = ui.langs_chip + " " + d.languages_customer_live_count;
        }
      } catch (err) {
        dot.classList.add("off");
        bind.textContent = (I18N[currentLocale] || I18N["ar-EG"]).offline;
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
        bubble("C5", (I18N[currentLocale] || I18N["ar-EG"]).conn_err, false);
      }
      pulse();
    }
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = box.value.trim();
      if (!text || btn.disabled) return;
      const ui = I18N[currentLocale] || I18N["ar-EG"];
      box.value = "";
      btn.disabled = true;
      btn.textContent = ui.sending;
      const mine = bubble("C1", text, false, new Date().toISOString());
      typing(true);
      try {
        const r = await fetch("/api/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({text, locale: currentLocale}),
        });
        const data = await r.json();
        typing(false);
        if (data.locale && I18N[data.locale] && data.locale !== currentLocale) applyLocale(data.locale);
        if (mine && (data.decoded || data.flipped)) {
          mine.querySelector(".bubble").textContent = data.decoded || text;
        }
        if (mine && data.flipped) {
          const meta = mine.querySelector(".meta");
          if (meta && !meta.querySelector(".flip")) meta.appendChild(el("span", "flip", (I18N[currentLocale] || I18N["ar-EG"]).flip));
        }
        bubble("C5", data.answer || ui.ground_empty, false, data.ts);
      } catch (err) {
        typing(false);
        bubble("C5", ui.conn_err, false);
      } finally {
        btn.disabled = false;
        btn.textContent = (I18N[currentLocale] || I18N["ar-EG"]).send;
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
    document.getElementById("lang-switch").addEventListener("click", (e) => {
      const node = e.target.closest("[data-locale]");
      if (!node) return;
      applyLocale(node.getAttribute("data-locale"));
    });
    applyLocale(bootLocale());
    boot();
    setInterval(pulse, 12000);
  </script>
</body>
</html>
"""
PAGE = PAGE.replace("__I18N__", json.dumps(I18N, ensure_ascii=False))


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
                    "languages_customer_live": card.get("languages_customer_live"),
                    "locales": list(LIVE_LOCALES),
                    "paid_api": False,
                    "gl005_proven": False,
                    "law": ["SAME_LOOPBACK_OR_PORT_FORWARD", "UNPOLISHED_SCREEN_NE_SHIP", "SCREEN_IS_MULTILINGUAL"],
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
            rec = teach_reply(str(data.get("text") or ""), locale=(str(data.get("locale") or "") or None))
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
