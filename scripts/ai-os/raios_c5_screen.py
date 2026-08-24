#!/usr/bin/env python3
"""C5 professional system screen. Open-source, local, standard. No paid API. No WAL."""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_keyboard import decode_flipped_keyboard, teach_text  # noqa: E402
from raios_c5_reason import ground  # noqa: E402
from raios_c5_whoami import c5_bind, control_plane_runtime, whoami  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
HISTORY = ROOT / ".ai-os" / "learning" / "C5-SCREEN.jsonl"
HISTORY_C1 = ROOT / ".ai-os" / "learning" / "C5-SCREEN-C1.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-screen"
SEAT_MAP = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"
PACKETS = ROOT / ".ai-os" / "mcp" / "packets.jsonl"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
C1_PORT = 8876
BIND_PORTS = (DEFAULT_PORT, C1_PORT)
LANE_PUBLIC = "PUBLIC"
LANE_C1 = "C1"
PUBLIC_PORT = DEFAULT_PORT
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
    "مين",
    "ما هو",
    "seat",
    "who is",
    "what is",
    "hva er",
    "rolle",
    "role",
    "rådet",
    "council",
    "role of",
)
SEAT_CODE_RE = re.compile(r"\bC(?:10|[0-9])s?\b", re.I)
UNSEATED_CODES = ("C6", "C7", "C8", "C9", "C10")
ABOLISHED_CODES = ("C0",)
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
        "note": "الشاشة على سيرفر التحكم المحلي 127.0.0.1:8765 — مش جلسة Cursor. على ويندوز: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Install ثم -Ensure.",
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
        "offline": "منقطع — شغّل الشاشة على السيرفر المحلي",
        "seat_role": "الدور الحي",
        "seat_where": "المكان",
        "seat_mail": "البريد",
        "yes": "نعم",
        "no": "لا",
        "seat_note": "ملاحظة",
        "seat_src": "المصدر: .ai-os/mcp/SEAT-MAP.json — بيان مقعد، ليست إجابة معرفية كاملة.",
        "empty_prompt": "اكتب رسالة لـ C5.",
        "ground_empty": "لا دليل كافٍ لصياغة رد نظيف من الاسترجاع المحلي. هذا ليس إثبات GL-005.",
        "conn_err": "تعذر الاتصال. الشاشة لازم تشتغل دائمًا على السيرفر المحلي 127.0.0.1:8765. جلسة Cursor مؤقتة.",
        "hello": "حيّ. أنا C5 على الشاشة المحلية.\nاكتب بالمصري أو الخليجي أو الإنجليزي أو النرويجي، أو بالكيبورد المقلوب. Enter للإرسال.",
        "screen": (
            "هذه شاشة التواصل مع C5 على سيرفر التحكم المحلي. متعددة اللغات: ar-EG، ar-GULF، en، nb-NO.\n"
            "الربط 127.0.0.1:8765 على السيرفر المحلي. جلسة Cursor ليست البيت.\n"
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
        "note": "الشاشة على سيرفر التحكم المحلي 127.0.0.1:8765 — مو جلسة Cursor. ويندوز: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Install بعدين -Ensure.",
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
        "offline": "منقطع — شغّل الشاشة على السيرفر المحلي",
        "seat_role": "الدور الحي",
        "seat_where": "المكان",
        "seat_mail": "البريد",
        "yes": "نعم",
        "no": "لا",
        "seat_note": "ملاحظة",
        "seat_src": "المصدر: .ai-os/mcp/SEAT-MAP.json — بيان مقعد، مو إجابة معرفية كاملة.",
        "empty_prompt": "اكتب رسالة لـ C5.",
        "ground_empty": "ما فيه دليل كافي لرد نظيف من الفهرس المحلي. هذا مو إثبات GL-005.",
        "conn_err": "تعذر الاتصال. الشاشة لازم تشتغل دائمًا على السيرفر المحلي 127.0.0.1:8765. جلسة Cursor مؤقتة.",
        "hello": "حياك. أنا C5 على الشاشة المحلية.\nاكتب بالخليجي أو المصري أو الإنجليزي أو النرويجي.",
        "screen": (
            "هذي شاشة التواصل مع C5 على سيرفر التحكم المحلي. اللغات: ar-EG، ar-GULF، en، nb-NO.\n"
            "الربط 127.0.0.1:8765 على السيرفر المحلي. جلسة Cursor مو البيت.\n"
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
        "note": "C5 screen lives on the local control-plane server at 127.0.0.1:8765 — not this Cursor session. Windows: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Install then -Ensure.",
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
        "offline": "offline — start the local control-plane screen",
        "seat_role": "Live role",
        "seat_where": "Where",
        "seat_mail": "Mail",
        "yes": "yes",
        "no": "no",
        "seat_note": "Note",
        "seat_src": "Source: .ai-os/mcp/SEAT-MAP.json — a seat statement, not a full cognitive answer.",
        "empty_prompt": "Write a message to C5.",
        "ground_empty": "Not enough local evidence for a clean reply. This is not GL-005 proof.",
        "conn_err": "Cannot reach the local control-plane screen at 127.0.0.1:8765. This Cursor session is SESSION_TEMP. Run -Install then -Ensure on the local server.",
        "hello": "Live. I am C5 on the local screen.\nWrite in Egyptian, Gulf Arabic, English, or Norwegian. Enter to send.",
        "screen": (
            "This is the C5 console on the local control-plane server. Locales: ar-EG, ar-GULF, en, nb-NO.\n"
            "Bind 127.0.0.1:8765 on that host. A Cursor session bind is SESSION_TEMP, not home.\n"
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
        "note": "C5-skjermen bor på den lokale control-plane-serveren 127.0.0.1:8765 — ikke denne Cursor-økten. Windows: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Install deretter -Ensure.",
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
        "offline": "frakoblet — start den lokale control-plane-skjermen",
        "seat_role": "Levende rolle",
        "seat_where": "Sted",
        "seat_mail": "Post",
        "yes": "ja",
        "no": "nei",
        "seat_note": "Merknad",
        "seat_src": "Kilde: .ai-os/mcp/SEAT-MAP.json — seteerklæring, ikke et fullt kognitivt svar.",
        "empty_prompt": "Skriv en melding til C5.",
        "ground_empty": "Ikke nok lokalt belegg for et rent svar. Dette er ikke GL-005-bevis.",
        "conn_err": "Får ikke kontakt. Skjermen skal kjøre varig på den lokale control-plane-serveren 127.0.0.1:8765. Cursor-økten er SESSION_TEMP.",
        "hello": "Live. Jeg er C5 på den lokale skjermen.\nSkriv på egyptisk, gulf-arabisk, engelsk eller norsk. Enter sender.",
        "screen": (
            "Dette er C5-konsollen på den lokale control-plane-serveren. Språk: ar-EG, ar-GULF, en, nb-NO.\n"
            "Binding 127.0.0.1:8765 på den verten. En Cursor-økt er SESSION_TEMP, ikke hjem.\n"
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

LANE_I18N = {
    "ar-EG": {
        "you": "زائر",
        "lane_public": "للجميع",
        "lane_c1": "لـ C1 فقط",
        "thread": "شاشة الجميع",
        "thread_c1": "شاشة C1",
        "public_note": "هذه شاشة C5 للجميع: عملاء وفريق. متعددة اللغات. مش شاشة المؤسس.",
        "c1_note": "هذه شاشتك أنت يا C1. المنفذ 8876. شاشة الجميع على 8765. نفس C5، مش C5 تاني. ويندوز: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Go",
        "c1_panel_h": "لوحة المؤسس",
        "public_url_k": "شاشة الجميع",
        "public_url_v": "http://127.0.0.1:8765",
        "c1_url_k": "شاشة C1",
        "c1_url_v": "http://127.0.0.1:8876",
        "mcp_k": "MCP",
        "mcp_v": "http://127.0.0.1:8787/mcp · 8 أدوات",
        "cortex_k": "قشرة مرشحة",
        "cortex_v": "qwen3.6:35b-a3b · ليست دائمة",
        "opencode_k": "OpenCode",
        "opencode_v": "CODE_MODEL · جسر تنفيذ",
        "ps1_k": "تثبيت ويندوز",
        "ps1_v": "raios_c5_screen.ps1 -Go",
        "chip_status": "حالة النظام",
        "fill_status": "حالة الشاشة",
        "chip_c6": "ما دور C6",
        "fill_c6": "ما دور C6",
        "c6_k": "وارد C6",
        "c6_v": "C6_LIVE=false",
        "public_whoami": (
            "أنا C5 — مساعد RAIOS للجميع. أردّ بالمصري والخليجي والإنجليزي والنرويجي من الملفات المحلية.\n"
            "مش OpenAI ومش LangChain. شاشة المؤسس منفصلة.\n"
            "الدور: شاشة C5 للجميع. المقاعد الحية C1–C5. C6_C10_NE_LIVE. IDENTITY_BEFORE_ACTION."
        ),
        "public_hello": "أهلاً. أنا C5 على شاشة الجميع.\nاكتب بالمصري أو الخليجي أو الإنجليزي أو النرويجي، أو بالكيبورد المقلوب.",
        "public_screen": (
            "هذه شاشة C5 للجميع على السيرفر المحلي. اللغات: ar-EG، ar-GULF، en، nb-NO.\n"
            "الربط 127.0.0.1:8765. الكيبورد المقلوب يُفك هنا. السجل محلي.\n"
            "ليس LangChain وليس OpenAI. شاشة C1 الخاصة على المنفذ 8876."
        ),
        "unseated": "{code} غير جالس. القانون C6_C10_NE_LIVE. المقاعد الحية: C1–C5. لا نختلق مقعد عشان الشكل.",
        "abolished": "C0 ملغى. سلطة المالك على C1. لا يوجد مقعد C0 حي.",
        "unseated_wait": (
            "في انتظار حزمة على MCP الحالي (8 أدوات: send_packet/ack_packet). "
            "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING. FOUNDER_RELAY_IS_THE_INBOUND_TRANSPORT. "
            "PASTED_CHAT_NE_MCP_ROUND_TRIP. C6_PACKET_NE_LIVE_SEAT. NO_NEW_MCP_TOOL."
        ),
    },
    "ar-GULF": {
        "you": "زائر",
        "lane_public": "للجميع",
        "lane_c1": "لـ C1 بس",
        "thread": "شاشة الجميع",
        "thread_c1": "شاشة C1",
        "public_note": "هذي شاشة C5 للجميع: عملاء وفريق. مو شاشة المؤسس.",
        "c1_note": "هذي شاشتك يا C1 على 8876. شاشة الجميع 8765. نفس C5. ويندوز: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Go",
        "c1_panel_h": "لوحة المؤسس",
        "public_url_k": "شاشة الجميع",
        "public_url_v": "http://127.0.0.1:8765",
        "c1_url_k": "شاشة C1",
        "c1_url_v": "http://127.0.0.1:8876",
        "mcp_k": "MCP",
        "mcp_v": "http://127.0.0.1:8787/mcp · 8 أدوات",
        "cortex_k": "قشرة مرشحة",
        "cortex_v": "qwen3.6:35b-a3b · مو دائمة",
        "opencode_k": "OpenCode",
        "opencode_v": "CODE_MODEL · جسر تنفيذ",
        "ps1_k": "تثبيت ويندوز",
        "ps1_v": "raios_c5_screen.ps1 -Go",
        "chip_status": "حالة النظام",
        "fill_status": "حالة الشاشة",
        "chip_c6": "ما دور C6",
        "fill_c6": "ما دور C6",
        "c6_k": "وارد C6",
        "c6_v": "C6_LIVE=false",
        "public_whoami": (
            "أنا C5 — مساعد RAIOS للجميع. أرد بالخليجي والمصري والإنجليزي والنرويجي من الملفات المحلية.\n"
            "مو OpenAI ومو LangChain. شاشة المؤسس منفصلة.\n"
            "الدور: شاشة C5 للجميع. المقاعد الحية C1–C5. C6_C10_NE_LIVE. IDENTITY_BEFORE_ACTION."
        ),
        "public_hello": "حياك. أنا C5 على شاشة الجميع.\nاكتب بالخليجي أو المصري أو الإنجليزي أو النرويجي.",
        "public_screen": (
            "هذي شاشة C5 للجميع على السيرفر المحلي. اللغات: ar-EG، ar-GULF، en، nb-NO.\n"
            "الربط 127.0.0.1:8765. مو LangChain ومو OpenAI. شاشة C1 على 8876."
        ),
        "unseated": "{code} مو جالس. القانون C6_C10_NE_LIVE. المقاعد الحية: C1–C5. ما نختلق مقعد.",
        "abolished": "C0 ملغي. السلطة عند C1. ما فيه مقعد C0 حي.",
        "unseated_wait": (
            "ننتظر حزمة على MCP الحالي (8 أدوات: send_packet/ack_packet). "
            "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING. FOUNDER_RELAY_IS_THE_INBOUND_TRANSPORT. "
            "PASTED_CHAT_NE_MCP_ROUND_TRIP. C6_PACKET_NE_LIVE_SEAT. NO_NEW_MCP_TOOL."
        ),
    },
    "en": {
        "you": "You",
        "lane_public": "for everyone",
        "lane_c1": "C1 only",
        "thread": "Shared screen",
        "thread_c1": "C1 console",
        "public_note": "This is the shared C5 screen for customers and the team. The founder console is separate.",
        "c1_note": "This is your C1 console on 8876. Shared screen is 8765. Same C5, not a second C5. Windows: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Go",
        "c1_panel_h": "Founder panel",
        "public_url_k": "Shared screen",
        "public_url_v": "http://127.0.0.1:8765",
        "c1_url_k": "C1 screen",
        "c1_url_v": "http://127.0.0.1:8876",
        "mcp_k": "MCP",
        "mcp_v": "http://127.0.0.1:8787/mcp · 8 tools",
        "cortex_k": "Named cortex",
        "cortex_v": "qwen3.6:35b-a3b · not permanent",
        "opencode_k": "OpenCode",
        "opencode_v": "CODE_MODEL execution bridge",
        "ps1_k": "Windows install",
        "ps1_v": "raios_c5_screen.ps1 -Go",
        "chip_status": "system status",
        "fill_status": "screen status",
        "chip_c6": "C6 role",
        "fill_c6": "What is C6's role",
        "c6_k": "C6 inbound",
        "c6_v": "C6_LIVE=false",
        "public_whoami": (
            "I am C5 — the shared RAIOS assistant. I answer in Egyptian, Gulf Arabic, English, and Norwegian from local files.\n"
            "Not OpenAI. Not LangChain. The founder console is separate.\n"
            "Role: shared C5 screen. Live seats C1–C5. C6_C10_NE_LIVE. IDENTITY_BEFORE_ACTION."
        ),
        "public_hello": "Hello. I am C5 on the shared screen.\nWrite in Egyptian, Gulf Arabic, English, or Norwegian — flipped keyboard is decoded.",
        "public_screen": (
            "This is the shared C5 screen on the local control-plane host. Locales: ar-EG, ar-GULF, en, nb-NO.\n"
            "Bind 127.0.0.1:8765. Not LangChain. Not OpenAI. The C1 console is on port 8876."
        ),
        "unseated": "{code} is not seated. Law C6_C10_NE_LIVE. Live seats are C1–C5. We do not invent a seat to look complete.",
        "abolished": "C0 is abolished. Owner authority lives on C1. There is no live C0 seat.",
        "unseated_wait": (
            "Waiting on the existing MCP bus (8 tools: send_packet/ack_packet). "
            "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING. FOUNDER_RELAY_IS_THE_INBOUND_TRANSPORT. "
            "PASTED_CHAT_NE_MCP_ROUND_TRIP. C6_PACKET_NE_LIVE_SEAT. NO_NEW_MCP_TOOL."
        ),
    },
    "nb-NO": {
        "you": "Du",
        "lane_public": "for alle",
        "lane_c1": "kun C1",
        "thread": "Delt skjerm",
        "thread_c1": "C1-konsoll",
        "public_note": "Dette er den delte C5-skjermen for kunder og team. Grunnleggerkonsollen er separat.",
        "c1_note": "Dette er C1-konsollen på 8876. Delt skjerm er 8765. Samme C5, ikke en nr. 2. Windows: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Go",
        "c1_panel_h": "Grunnleggerpanel",
        "public_url_k": "Delt skjerm",
        "public_url_v": "http://127.0.0.1:8765",
        "c1_url_k": "C1-skjerm",
        "c1_url_v": "http://127.0.0.1:8876",
        "mcp_k": "MCP",
        "mcp_v": "http://127.0.0.1:8787/mcp · 8 verktøy",
        "cortex_k": "Navngitt cortex",
        "cortex_v": "qwen3.6:35b-a3b · ikke permanent",
        "opencode_k": "OpenCode",
        "opencode_v": "CODE_MODEL-kjøringsbro",
        "ps1_k": "Windows-installasjon",
        "ps1_v": "raios_c5_screen.ps1 -Go",
        "chip_status": "systemstatus",
        "fill_status": "skjermstatus",
        "chip_c6": "C6s rolle",
        "fill_c6": "Hva er C6s rolle",
        "c6_k": "C6 innkommende",
        "c6_v": "C6_LIVE=false",
        "public_whoami": (
            "Jeg er C5 — den delte RAIOS-assistenten. Jeg svarer på egyptisk, gulf-arabisk, engelsk og norsk fra lokale filer.\n"
            "Ikke OpenAI. Ikke LangChain. Grunnleggerkonsollen er separat.\n"
            "Rolle: delt C5-skjerm. Levende seter C1–C5. C6_C10_NE_LIVE. IDENTITY_BEFORE_ACTION."
        ),
        "public_hello": "Hei. Jeg er C5 på den delte skjermen.\nSkriv på egyptisk, gulf-arabisk, engelsk eller norsk.",
        "public_screen": (
            "Dette er den delte C5-skjermen på den lokale control-plane-verten. Språk: ar-EG, ar-GULF, en, nb-NO.\n"
            "Binding 127.0.0.1:8765. Ikke LangChain. Ikke OpenAI. C1-konsollen er på port 8876."
        ),
        "unseated": "{code} er ikke satt. Lov C6_C10_NE_LIVE. Levende seter er C1–C5. Vi finner ikke opp et sete for å se komplette ut.",
        "abolished": "C0 er avskaffet. Eierautoritet ligger hos C1. Det finnes ikke et levende C0-sete.",
        "unseated_wait": (
            "Venter på eksisterende MCP-buss (8 verktøy: send_packet/ack_packet). "
            "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING. FOUNDER_RELAY_IS_THE_INBOUND_TRANSPORT. "
            "PASTED_CHAT_NE_MCP_ROUND_TRIP. C6_PACKET_NE_LIVE_SEAT. NO_NEW_MCP_TOOL."
        ),
    },
}
for _loc, _extra in LANE_I18N.items():
    I18N[_loc].update(_extra)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def lane_of_port(port: int | None) -> str:
    return LANE_C1 if int(port or DEFAULT_PORT) == C1_PORT else LANE_PUBLIC


def history_path(lane: str | None = None) -> Path:
    return HISTORY_C1 if lane == LANE_C1 else HISTORY


def c1_token_expected() -> str:
    return (os.environ.get("RAIOS_C1_SCREEN_TOKEN") or "").strip()


def c1_request_allowed(handler: BaseHTTPRequestHandler) -> bool:
    expected = c1_token_expected()
    if not expected:
        return True
    if handler.headers.get("X-RAIOS-C1-Token") == expected:
        return True
    query = parse_qs(urlparse(handler.path).query)
    if (query.get("token") or [""])[0] == expected:
        return True
    cookie = handler.headers.get("Cookie") or ""
    return f"raios_c1={expected}" in cookie


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def c6_inbound_state() -> dict:
    """Read-only inbound census. Packet seen ≠ live seat. Does not ack."""
    seen = 0
    last_id = None
    if PACKETS.is_file():
        for line in PACKETS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            head = str(row.get("from") or "").strip().split("/", 1)[0].upper()
            if head == "C6":
                seen += 1
                last_id = row.get("packet_id") or last_id
    inbound = "seen" if seen else "waiting"
    return {
        "c6_live": False,
        "C6_LIVE": False,
        "c6_inbound": inbound,
        "C6_INBOUND": inbound,
        "c6_packets_seen": seen,
        "c6_last_packet_id": last_id,
        "mcp_packet_received": False,
        "mcp_round_trip": False,
    }


def screen_health(*, host: str = DEFAULT_HOST, port: int | None = None) -> dict:
    """Same C5 process health. Honest cortex flag from probe(), not a printed MAIN_CORTEX."""
    bind = c5_bind()
    ports = list(bind.get("c5_screen_ports") or BIND_PORTS)
    bound_port = DEFAULT_PORT if port is None else int(port)
    lane = lane_of_port(bound_port)
    rec = {
        "schema": "raios.c5-health.v1",
        "ok": True,
        "from": "C5",
        "http": 200,
        "host": host,
        "port": bound_port,
        "lane": lane,
        "public_url": f"http://{host}:{PUBLIC_PORT}",
        "c1_url": f"http://{host}:{C1_PORT}",
        "bind": f"{host}:{bound_port}",
        "ports": ports,
        "urls": [f"http://{host}:{p}" for p in ports],
        "duplicate_c5": False,
        "duplicate_router": False,
        "duplicate_mcp": False,
        "paid_api": False,
        "gl005_proven": False,
        **bind,
    }
    rec["HEALTH"] = 200
    rec["MAIN_CORTEX"] = bool(rec.get("main_cortex"))
    rec["MODEL"] = rec.get("bound_model") or rec.get("cortex_model")
    rec["NAMED_CANDIDATE"] = rec.get("named_candidate")
    rec["BOUND_MODEL"] = rec.get("bound_model") or rec.get("cortex_model")
    rec["PERMANENT_IDENTITY"] = False
    rec["LOCAL_WINNER"] = False
    rec["ROLE"] = "CORTEX_MODEL"
    rec["LAPTOP_IS_MODEL_HOST"] = False
    rec["OLLAMA_IS_DEV_FALLBACK"] = True
    rec["TRANSPORT"] = "openai-compatible"
    rec["law"] = [
        "SAME_C5_DUAL_BIND",
        "PUBLIC_SCREEN_NE_C1_CONSOLE",
        "C1_CONSOLE_NE_SECOND_C5",
        "HEALTH_200_NE_CORTEX_LIVE",
        "PROBE_IS_CORTEX_TRUTH",
        "STUDENT_NE_CORTEX",
        "CURRENT_WINNERS_ARE_NOT_FINAL",
        "RAIOS_NE_ONE_MODEL",
        "LAPTOP_NE_MODEL_HOST",
        "OLLAMA_IS_DEV_FALLBACK",
        "LOCAL_OLLAMA_NE_CORTEX_CRITERION",
        "OPENAI_COMPAT_TRANSPORT",
        "ROLE_NE_HARDCODED_IDENTITY",
        "NAMED_CANDIDATE_NE_PERMANENT_CORTEX",
        "NO_DUPLICATE_MCP",
        "NO_DUPLICATE_COUNCIL",
        "NO_DUPLICATE_REGISTRY",
        "C5_SCREEN_NE_CURSOR_SESSION",
        "C5_SCREEN_LIVES_ON_CONTROL_PLANE",
        "CURSOR_SCREEN_IS_SESSION_TEMP",
        "IDENTITY_BEFORE_ACTION",
        "C6_C10_NE_LIVE",
        "C6_PACKET_NE_LIVE_SEAT",
        "PASTED_CHAT_NE_MCP_ROUND_TRIP",
        "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING",
        "FOUNDER_RELAY_IS_THE_INBOUND_TRANSPORT",
        "NO_NEW_MCP_TOOL",
    ]
    rec["screen_home"] = bind.get("screen_home")
    rec["screen_durable"] = bool(bind.get("screen_durable"))
    rec["cursor_session_ne_c5"] = True
    rec["this_host_is_cursor_cloud"] = bool(bind.get("this_host_is_cursor_cloud"))
    inbound = c6_inbound_state()
    rec.update(inbound)
    rec["C6_LIVE"] = False
    rec["c6_live"] = False
    rec["mcp_packet_received"] = False
    rec["mcp_round_trip"] = False
    return rec


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


def load_history(limit: int = 24, lane: str | None = None) -> list[dict]:
    path = history_path(lane)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
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


def append_history(row: dict, lane: str | None = None) -> None:
    path = history_path(lane)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
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


def _identity_reply(card: dict, locale: str, lane: str = LANE_PUBLIC) -> str:
    langs = "، ".join(str(x) for x in card.get("languages_customer_live") or []) if locale.startswith("ar") else ", ".join(str(x) for x in card.get("languages_customer_live") or [])
    engine = card["engine_now"]["inject"]
    key = "whoami" if lane == LANE_C1 else "public_whoami"
    text = pack(locale)[key]
    if "{engine}" in text:
        return text.format(
            engine=engine,
            n=card.get("languages_customer_live_count"),
            langs=langs,
        )
    return text


def _screen_reply(locale: str, lane: str = LANE_PUBLIC) -> str:
    ui = pack(locale)
    return ui["screen"] if lane == LANE_C1 else ui["public_screen"]


def _hello_reply(locale: str, lane: str = LANE_PUBLIC) -> str:
    ui = pack(locale)
    return ui["hello"] if lane == LANE_C1 else ui["public_hello"]


def _seat_codes(query: str) -> list[str]:
    codes: list[str] = []
    for raw in SEAT_CODE_RE.findall(query or ""):
        digits = re.search(r"\d+", raw)
        if not digits:
            continue
        codes.append("C" + digits.group(0))
    return list(dict.fromkeys(codes))


def _seat_intent(query: str) -> bool:
    blob = f"{query} {(query or '').lower()}"
    return any(mark.lower() in blob.lower() or mark in (query or "") for mark in SEAT_MARKS)


def _seat_card(query: str, locale: str = "ar-EG") -> str | None:
    codes = _seat_codes(query)
    if not codes:
        return None
    intent = _seat_intent(query)
    ui = pack(locale)
    inbound = c6_inbound_state()
    seats: dict = {}
    if SEAT_MAP.is_file():
        try:
            seats = json.loads(SEAT_MAP.read_text(encoding="utf-8")).get("seats") or {}
        except json.JSONDecodeError:
            seats = {}
    capability = {
        "C1": "founder / CONTROL_PLANE_ONLY. does not impersonate C5 or C6.",
        "C2": "consultant. MCP or mail. not C5. not C6. packet alias C2/CURSOR is executor, not a new live seat.",
        "C3": "consultant peer. not Repair. not C5. not C6.",
        "C4": "assessor. MCP or mail. does not execute. not C5. not C6.",
        "C5": "RAIOS. shared PUBLIC screen + C1 console. MCP 8 tools. not a second C5. not C6.",
    }
    blocks: list[str] = []
    for code in codes:
        if code in ABOLISHED_CODES:
            blocks.append(ui["abolished"] + "\nIDENTITY_BEFORE_ACTION. C0_SEAT_ABOLISHED.")
            continue
        if code in UNSEATED_CODES:
            wait = ui.get("unseated_wait") or (
                "Waiting on the existing MCP bus (8 tools: send_packet/ack_packet). "
                "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING. FOUNDER_RELAY_IS_THE_INBOUND_TRANSPORT. "
                "PASTED_CHAT_NE_MCP_ROUND_TRIP. C6_PACKET_NE_LIVE_SEAT. NO_NEW_MCP_TOOL."
            )
            blocks.append(
                f"{ui['unseated'].format(code=code)}\n"
                f"C6_LIVE=false. C6_C10_NE_LIVE. IDENTITY_BEFORE_ACTION.\n"
                f"C6_INBOUND={inbound.get('c6_inbound')}. packets_seen={inbound.get('c6_packets_seen')}. "
                f"MCP_PACKET_RECEIVED=false.\n"
                f"{wait}"
            )
            continue
        if not intent:
            continue
        row = seats.get(code) or {}
        if not row:
            continue
        name = row.get("name_en") if locale in {"en", "nb-NO"} else (row.get("name_ar") or row.get("name_en"))
        mail = ui["yes"] if row.get("mail") else ui["no"]
        notes = str(row.get("notes") or "").strip()
        tools = ", ".join(str(t) for t in (row.get("tools") or [])[:8])
        block = (
            f"{code} — {name or code}\n"
            f"{ui['seat_role']}: {row.get('actor_role')} · {row.get('instance_role')}\n"
            f"{ui['seat_where']}: {row.get('where') or '—'}\n"
            f"{ui['seat_mail']}: {mail}\n"
            f"IDENTITY_BEFORE_ACTION. capability: {capability.get(code, row.get('actor_role'))}. "
            f"live seats = C1-C5. C6_C10_NE_LIVE."
        )
        if tools:
            block += f"\n{ui['tools_k']}: {tools}"
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


def _is_status(text: str) -> bool:
    t = (text or "").strip().lower().rstrip("!؟?.")
    return t in {
        "حالة الشاشة",
        "حالة النظام",
        "screen status",
        "system status",
        "skjermstatus",
        "status",
    }


def _status_reply(locale: str, lane: str) -> str:
    rec = screen_health(port=C1_PORT if lane == LANE_C1 else PUBLIC_PORT)
    ui = pack(locale)
    return (
        f"{ui['lane_c1'] if lane == LANE_C1 else ui['lane_public']}\n"
        f"{ui['public_url_k']}: {rec.get('public_url')}\n"
        f"{ui['c1_url_k']}: {rec.get('c1_url')}\n"
        f"MCP: {rec.get('mcp_endpoint') or 'http://127.0.0.1:8787/mcp'} tools={rec.get('mcp_tool_count')}\n"
        f"SCREEN_HOME={rec.get('screen_home')} durable={str(bool(rec.get('screen_durable'))).lower()}\n"
        f"MAIN_CORTEX={str(bool(rec.get('MAIN_CORTEX'))).lower()} MODEL={rec.get('MODEL')}\n"
        f"PERMANENT_IDENTITY=false LOCAL_WINNER=false GL005_PROVEN=false duplicate_c5=false\n"
        f"IDENTITY_BEFORE_ACTION. C6_LIVE=false C6_INBOUND={rec.get('c6_inbound')} "
        f"packets_seen={rec.get('c6_packets_seen')} MCP_PACKET_RECEIVED=false"
    )


def teach_reply(message: str, locale: str | None = None, lane: str | None = None) -> dict:
    wal_before = wal_mtime()
    lane = LANE_C1 if lane == LANE_C1 else LANE_PUBLIC
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
            "lane": lane,
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
    status = lane == LANE_C1 and (_is_status(orig_norm) or _is_status(lowered))
    screen = any(mark in lowered for mark in SCREEN_MARKS) or any(
        mark in lowered.lower() or mark in orig_norm.lower() for mark in SCREEN_MARKS
    )
    if identity:
        loc = detect_locale(orig_norm, locale)
        ui = pack(loc)
        answer = _identity_reply(whoami(), loc, lane)
        kind = "whoami"
    elif hello:
        loc = detect_locale(orig_norm, locale)
        ui = pack(loc)
        answer = _hello_reply(loc, lane)
        kind = "hello"
    elif status:
        loc = detect_locale(orig_norm, locale)
        answer = _status_reply(loc, lane)
        kind = "status"
    elif screen:
        loc = detect_locale(orig_norm if not kb.get("applied") else text, locale)
        ui = pack(loc)
        answer = _screen_reply(loc, lane)
        kind = "screen"
    else:
        query = text if kb.get("applied") else orig_norm
        seat = _seat_card(query, loc)
        if seat:
            answer = seat
            kind = "ground"
            chat_rec = None
        else:
            from raios_c5_speak import chat

            chat_rec = asyncio.run(chat(query))
            answer = str(chat_rec.get("answer") or "")
            kind = "speak"
    rec = {
        "schema": "raios.c5-screen-turn.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "kind": kind,
        "lane": lane,
        "locale": loc,
        "original": message,
        "decoded": text,
        "flipped": bool(kb.get("applied")),
        "answer": answer if kind in {"speak", "status"} else (present_answer(answer) or answer),
        "paid_api": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "C5_SCREEN_IS_STANDARD",
            "SCREEN_IS_MULTILINGUAL",
            "FLIPPED_KEYBOARD_IS_INPUT",
            "UNPOLISHED_SCREEN_NE_SHIP",
            "SCREEN_REPLY_NE_INDEX_DUMP",
            "PUBLIC_SCREEN_NE_C1_CONSOLE",
            "C1_CONSOLE_NE_SECOND_C5",
            "C5_SCREEN_LIVES_ON_CONTROL_PLANE",
            "CURSOR_SCREEN_IS_SESSION_TEMP",
            "HUNT_FREE_NE_PAID_API",
            "INDEX_HIT_NE_REASONING",
            "FILE_DISCOVERY_NE_FILE_ASSIMILATION",
            "RETRIEVAL_RESULT_NE_COGNITIVE_ANSWER",
            "ROLE_IDENTITY_NE_MODEL_IDENTITY",
            "IDENTITY_BEFORE_ACTION",
            "C6_C10_NE_LIVE",
            "C6_PACKET_NE_LIVE_SEAT",
            "PASTED_CHAT_NE_MCP_ROUND_TRIP",
        ],
    }
    if kind == "speak":
        rec["model"] = chat_rec.get("model")
        rec["cortex_model"] = chat_rec.get("cortex_model")
        rec["role"] = chat_rec.get("role")
        rec["role_bound"] = chat_rec.get("role_bound")
        rec["model_agnostic"] = chat_rec.get("model_agnostic")
        rec["local_winner"] = False
        rec["winner_final"] = False
        rec["endpoint_kind"] = chat_rec.get("endpoint_kind")
        rec["endpoint_configured"] = chat_rec.get("endpoint_configured")
        rec["laptop_is_model_host"] = False
        rec["transport"] = chat_rec.get("transport") or "openai-compatible"
        rec["model_name_bound"] = chat_rec.get("model_name_bound")
        rec["llm_executed"] = chat_rec.get("llm_executed")
        rec["real_llm_execution"] = chat_rec.get("real_llm_execution")
        rec["provider_execute_called"] = chat_rec.get("provider_execute_called")
        rec["error"] = chat_rec.get("error")
        rec["student_substituted"] = False
        rec["c5_to_neurolingua"] = True
        rec["neurolingua_to_provider"] = True
        rec["provider_to_model"] = chat_rec.get("provider_to_model")
        rec["model_response_to_c5"] = True
        rec["law"] = list(rec["law"]) + ["C5_SCREEN_TO_NEUROLINGUA", "STUDENT_NE_CORTEX"]
        if chat_rec.get("error") == "WAL_VIOLATION":
            raise SystemExit("SCREEN_WAL_VIOLATION")
    if wal_mtime() != wal_before:
        raise SystemExit("SCREEN_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    rec["ok"] = True
    rec["stored"] = True
    append_history(rec, lane)
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
    body.lane-PUBLIC .c1-only { display: none !important; }
    body.lane-C1 .public-only { display: none !important; }
    body.lane-C1 { --accent: #c9a227; --accent-dim: #3d3414; }
  </style>
</head>
<body class="lane-__LANE__">
  <div class="app">
    <header class="top">
      <div class="brand">
        <span id="live-dot" class="pulse" title="حي"></span>
        <div>
          <h1 id="live-title">C5 · RAIOS</h1>
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
        <span class="chip public-only" data-i18n="lane_public">للجميع</span>
        <span class="chip c1-only" data-i18n="lane_c1">لـ C1 فقط</span>
        <span class="chip c1-only">GL005 <strong>false</strong></span>
        <span class="chip">paid_api <strong>false</strong></span>
        <span class="chip" id="live-lang">لغات العملاء 4</span>
      </div>
    </header>
    <div class="shell">
      <aside>
        <h2 data-i18n="identity_h">هوية التشغيل</h2>
        <div class="row public-only"><div class="k" data-i18n="customer_k">كلام العملاء</div><div class="v" data-i18n="customer_v">ar-EG · ar-GULF · en · nb-NO</div></div>
        <div class="row public-only"><div class="k" data-i18n="tools_k">الأدوات</div><div class="v" data-i18n="tools_v">Python stdlib · git · Ollama محلي</div></div>
        <div class="row public-only"><div class="k" data-i18n="forbid_k">ممنوع</div><div class="v" data-i18n="forbid_v">LangChain · OpenAI · Chroma · PASS</div></div>
        <div class="row c1-only"><div class="k" data-i18n="father_k">الأب</div><div class="v" data-i18n="father_v">C1 المالك</div></div>
        <div class="row c1-only"><div class="k" data-i18n="where_k">المكان</div><div class="v" data-i18n="where_v">git · ليس جلسة Cursor</div></div>
        <div class="row c1-only"><div class="k" data-i18n="engine_k">محرك التعلّم</div><div class="v" data-i18n="engine_v">mind-fill → INDEX → NeuroLingua</div></div>
        <div class="row c1-only"><div class="k" data-i18n="customer_k">كلام العملاء</div><div class="v" data-i18n="customer_v">ar-EG · ar-GULF · en · nb-NO</div></div>
        <div class="row c1-only"><div class="k" data-i18n="tools_k">الأدوات</div><div class="v" data-i18n="tools_v">Python stdlib · git · Ollama محلي</div></div>
        <div class="row c1-only"><div class="k" data-i18n="forbid_k">ممنوع</div><div class="v" data-i18n="forbid_v">LangChain · OpenAI · Chroma · PASS</div></div>
        <h2 class="c1-only" data-i18n="c1_panel_h">لوحة المؤسس</h2>
        <div class="row c1-only"><div class="k" data-i18n="public_url_k">شاشة الجميع</div><div class="v" data-i18n="public_url_v">http://127.0.0.1:8765</div></div>
        <div class="row c1-only"><div class="k" data-i18n="c1_url_k">شاشة C1</div><div class="v" data-i18n="c1_url_v">http://127.0.0.1:8876</div></div>
        <div class="row c1-only"><div class="k" data-i18n="mcp_k">MCP</div><div class="v" data-i18n="mcp_v">http://127.0.0.1:8787/mcp · 8 أدوات</div></div>
        <div class="row c1-only"><div class="k" data-i18n="cortex_k">قشرة مرشحة</div><div class="v" data-i18n="cortex_v">qwen3.6:35b-a3b · ليست دائمة</div></div>
        <div class="row c1-only"><div class="k" data-i18n="opencode_k">OpenCode</div><div class="v" data-i18n="opencode_v">CODE_MODEL · جسر تنفيذ</div></div>
        <div class="row c1-only"><div class="k" data-i18n="ps1_k">تثبيت ويندوز</div><div class="v">raios_c5_screen.ps1 -Go</div></div>
        <div class="row c1-only"><div class="k" data-i18n="c6_k">وارد C6</div><div class="v" id="live-c6" data-i18n="c6_v">C6_LIVE=false</div></div>
        <p class="note public-only" data-i18n="public_note">هذه شاشة C5 للجميع: عملاء وفريق. متعددة اللغات. مش شاشة المؤسس.</p>
        <p class="note c1-only" data-i18n="c1_note">هذه شاشتك أنت يا C1. المنفذ 8876. شاشة الجميع على 8765. نفس C5، مش C5 تاني. ويندوز: powershell -File scripts/ai-os/raios_c5_screen.ps1 -Go</p>
        <p class="note" data-i18n="note">هذه القناة على حلقة الجهاز نفسه. إذا رفض المتصفح الاتصال، فأنت على localhost جهاز آخر. استخدم تمرير منفذ Cursor إلى 8765.</p>
      </aside>
      <main>
        <div class="thread-head">
          <strong data-i18n="thread">شاشة الجميع</strong>
          <span data-i18n="thread_sub">الكيبورد المقلوب يُفك تلقائيًا · السجل يُكمَّل لما ترجع · متعدد اللغات</span>
        </div>
        <div id="log" role="log" aria-live="polite">
          <div class="empty" id="empty">
            <h3 data-i18n="empty_h">ابدأ المحادثة</h3>
            <p data-i18n="empty_p">اكتب بالعربي أو بالكيبورد المقلوب. الرد من الملفات المحلية، بلا API مدفوع.</p>
            <div class="examples">
              <button type="button" data-fill="مين أنت" data-i18n="chip_who">مين أنت</button>
              <button type="button" data-fill="ما دور C4 في المجلس" data-i18n="chip_c4">دور C4</button>
              <button type="button" data-fill="DULG AHAM" data-i18n="chip_flip">كيبورد مقلوب</button>
              <button type="button" class="c1-only" data-fill="حالة الشاشة" data-i18n="chip_status">حالة النظام</button>
              <button type="button" class="c1-only" data-fill="ما دور C6" data-i18n="chip_c6">ما دور C6</button>
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
              <button type="button" class="c1-only" data-fill="حالة الشاشة" data-i18n="chip_status">حالة النظام</button>
              <button type="button" class="c1-only" data-fill="ما دور C6" data-i18n="chip_c6">ما دور C6</button>
            </span>
            <span data-i18n="hint">Enter للإرسال · Shift+Enter سطر جديد · ليست LangChain وليست OpenAI</span>
          </div>
        </form>
      </main>
    </div>
  </div>
  <script>
    const I18N = __I18N__;
    const LANE = "__LANE__";
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
      const title = document.getElementById("live-title");
      if (title) title.textContent = LANE === "C1" ? "C1 · C5" : "C5 · RAIOS";
      document.title = LANE === "C1" ? "C1 · C5" : "C5 · RAIOS";
      document.querySelectorAll("[data-i18n]").forEach((node) => {
        const key = node.getAttribute("data-i18n");
        const useKey = (key === "thread" && LANE === "C1") ? "thread_c1" : key;
        if (ui[useKey]) node.textContent = ui[useKey];
      });
      document.querySelectorAll("[data-i18n='chip_who']").forEach((n) => n.setAttribute("data-fill", ui.fill_who));
      document.querySelectorAll("[data-i18n='chip_c4']").forEach((n) => n.setAttribute("data-fill", ui.fill_c4));
      document.querySelectorAll("[data-i18n='chip_flip']").forEach((n) => n.setAttribute("data-fill", ui.fill_flip));
      document.querySelectorAll("[data-i18n='chip_status']").forEach((n) => n.setAttribute("data-fill", ui.fill_status));
      document.querySelectorAll("[data-i18n='chip_c6']").forEach((n) => n.setAttribute("data-fill", ui.fill_c6));
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
    function userRole() {
      const ui = I18N[currentLocale] || I18N["ar-EG"];
      return LANE === "C1" ? "C1" : (ui.you || "You");
    }
    function bubble(role, text, flip, ts, mine) {
      const wrap = el("div", "msg " + (mine ? "me" : "him"));
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
        const c6 = document.getElementById("live-c6");
        if (c6) {
          c6.textContent = "C6_LIVE=false · inbound " + (d.c6_inbound || "waiting") + " · packets=" + (d.c6_packets_seen || 0);
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
          bubble(userRole(), row.decoded || row.original || "", row.flipped, row.ts, true);
          bubble("C5", row.answer || "", false, row.ts, false);
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
      const mine = bubble(userRole(), text, false, new Date().toISOString(), true);
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
        bubble("C5", data.answer || ui.ground_empty, false, data.ts, false);
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
PAGE_TEMPLATE = PAGE


def render_page(lane: str = LANE_PUBLIC) -> str:
    lane = LANE_C1 if lane == LANE_C1 else LANE_PUBLIC
    return PAGE_TEMPLATE.replace("__I18N__", json.dumps(I18N, ensure_ascii=False)).replace("__LANE__", lane)


PAGE = None
PAGE_PUBLIC = None
PAGE_C1 = None


def pages() -> tuple[str, str]:
    global PAGE, PAGE_PUBLIC, PAGE_C1
    if PAGE_PUBLIC is None:
        PAGE_PUBLIC = render_page(LANE_PUBLIC)
        PAGE_C1 = render_page(LANE_C1)
        PAGE = PAGE_PUBLIC
    return PAGE_PUBLIC, PAGE_C1


pages()


class Handler(BaseHTTPRequestHandler):
    bind_host = DEFAULT_HOST
    bind_port = DEFAULT_PORT
    bind_ports = BIND_PORTS

    @property
    def lane(self) -> str:
        return lane_of_port(getattr(self, "bind_port", DEFAULT_PORT))

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("C5-SCREEN " + (fmt % args) + "\n")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _gate_c1(self) -> bool:
        if self.lane != LANE_C1:
            return True
        if c1_request_allowed(self):
            return True
        rec = {"ok": False, "from": "C5", "lane": LANE_C1, "error": "C1_TOKEN_REQUIRED", "gl005_proven": False}
        self._send(403, json.dumps(rec, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        return False

    def do_GET(self) -> None:
        if not self._gate_c1():
            return
        path = urlparse(self.path).path
        public_html, c1_html = pages()
        if path in {"/", "/index.html"}:
            html = c1_html if self.lane == LANE_C1 else public_html
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path in {"/health", "/api/health"}:
            rec = screen_health(host=self.bind_host, port=self.bind_port)
            rec["port"] = self.bind_port
            rec["lane"] = self.lane
            rec["bind"] = f"{self.bind_host}:{self.bind_port}"
            rec["ports"] = list(getattr(self, "bind_ports", BIND_PORTS))
            payload = json.dumps(rec, ensure_ascii=False).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        if path == "/api/history":
            payload = json.dumps(
                {"turns": load_history(lane=self.lane), "lane": self.lane, "gl005_proven": False},
                ensure_ascii=False,
            ).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        if path == "/api/status":
            card = whoami()
            bind = card.get("c5_bind") or {}
            inbound = c6_inbound_state()
            payload = json.dumps(
                {
                    "ok": True,
                    "from": "C5",
                    "host": self.bind_host,
                    "port": self.bind_port,
                    "lane": self.lane,
                    "bind": f"{self.bind_host}:{self.bind_port}",
                    "ports": list(getattr(self, "bind_ports", BIND_PORTS)),
                    "public_url": f"http://{self.bind_host}:{PUBLIC_PORT}",
                    "c1_url": f"http://{self.bind_host}:{C1_PORT}",
                    "languages_customer_live_count": card.get("languages_customer_live_count"),
                    "languages_customer_live": card.get("languages_customer_live"),
                    "locales": list(LIVE_LOCALES),
                    "main_cortex": bool(bind.get("main_cortex")) if self.lane == LANE_C1 else False,
                    "cortex_model": bind.get("cortex_model") if self.lane == LANE_C1 else None,
                    "mcp_reachable": bind.get("mcp_reachable") if self.lane == LANE_C1 else None,
                    "council_seat_map": bind.get("council_seat_map") if self.lane == LANE_C1 else None,
                    "model_registry": bind.get("model_registry") if self.lane == LANE_C1 else None,
                    "screen_home": bind.get("screen_home"),
                    "screen_durable": bool(bind.get("screen_durable")),
                    "cursor_session_ne_c5": True,
                    "this_host_is_cursor_cloud": bool(bind.get("this_host_is_cursor_cloud")),
                    "paid_api": False,
                    "gl005_proven": False,
                    "duplicate_c5": False,
                    "c6_live": False,
                    "C6_LIVE": False,
                    "c6_inbound": inbound.get("c6_inbound"),
                    "c6_packets_seen": inbound.get("c6_packets_seen"),
                    "mcp_packet_received": False,
                    "law": [
                        "C5_SCREEN_LIVES_ON_CONTROL_PLANE",
                        "CURSOR_SCREEN_IS_SESSION_TEMP",
                        "UNPOLISHED_SCREEN_NE_SHIP",
                        "SCREEN_IS_MULTILINGUAL",
                        "PUBLIC_SCREEN_NE_C1_CONSOLE",
                        "C1_CONSOLE_NE_SECOND_C5",
                        "IDENTITY_BEFORE_ACTION",
                        "C6_C10_NE_LIVE",
                        "C6_PACKET_NE_LIVE_SEAT",
                        "PASTED_CHAT_NE_MCP_ROUND_TRIP",
                    ],
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if not self._gate_c1():
            return
        if urlparse(self.path).path != "/api/chat":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(min(length, 80_000)).decode("utf-8")
        try:
            data = json.loads(raw or "{}")
            rec = teach_reply(
                str(data.get("text") or ""),
                locale=(str(data.get("locale") or "") or None),
                lane=self.lane,
            )
        except Exception as exc:
            rec = {"ok": False, "from": "C5", "lane": self.lane, "answer": "تعذر الرد.", "error": type(exc).__name__, "gl005_proven": False}
            self._send(200, json.dumps(rec, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        self._send(200, json.dumps(rec, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")


def serve(host: str | None = None, ports: tuple[int, ...] | list[int] | None = None) -> None:
    """One C5 screen, two loopbacks. Not a second C5. Home is the control-plane host."""
    home = control_plane_runtime()
    host = host or home["bind_host"]
    wanted = tuple(ports or BIND_PORTS)
    Handler.bind_host = host
    Handler.bind_ports = wanted
    servers: list[tuple[int, ThreadingHTTPServer]] = []
    for port in wanted:
        handler = type(
            f"C5Handler{port}",
            (Handler,),
            {"bind_host": host, "bind_port": port, "bind_ports": wanted},
        )
        try:
            httpd = ThreadingHTTPServer((host, port), handler)
        except OSError as err:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "from": "C5",
                        "url": f"http://{host}:{port}",
                        "error": type(err).__name__,
                        "duplicate_c5": False,
                        "screen_home": home["screen_home"],
                        "screen_durable": bool(home["durable"]),
                        "cursor_session_ne_c5": True,
                        "gl005_proven": False,
                    },
                    ensure_ascii=False,
                )
            )
            continue
        servers.append((port, httpd))
        print(
            json.dumps(
                {
                    "ok": True,
                    "url": f"http://{host}:{port}",
                    "from": "C5",
                    "lane": lane_of_port(port),
                    "ports": list(wanted),
                    "public_url": f"http://{host}:{PUBLIC_PORT}",
                    "c1_url": f"http://{host}:{C1_PORT}",
                    "duplicate_c5": False,
                    "screen_home": home["screen_home"],
                    "screen_durable": bool(home["durable"]),
                    "cursor_session_ne_c5": True,
                    "gl005_proven": False,
                },
                ensure_ascii=False,
            )
        )
    if not servers:
        raise SystemExit("C5_SCREEN_NO_BIND")
    for _port, httpd in servers[:-1]:
        threading.Thread(target=httpd.serve_forever, name=f"c5-screen-{_port}", daemon=True).start()
    servers[-1][1].serve_forever()


def resolve_serve_args(argv: list[str]) -> tuple[str, tuple[int, ...]]:
    host = control_plane_runtime()["bind_host"]
    extra: list[str] = []
    args = [a for a in argv[1:] if a not in {"--serve", "--self-check"}]
    i = 0
    while i < len(args):
        if args[i] in {"--host", "-H"} and i + 1 < len(args):
            host = str(args[i + 1]).strip() or host
            i += 2
            continue
        extra.append(args[i])
        i += 1
    ports = BIND_PORTS
    if extra:
        ports = tuple(dict.fromkeys((*BIND_PORTS, int(extra[0]))))
    return host, ports


def main() -> int:
    if "--self-check" in sys.argv:
        rec = teach_reply("DULG AHAM")
        print(json.dumps({"ok": rec["ok"], "decoded": rec["decoded"], "flipped": rec["flipped"], "gl005_proven": False}, ensure_ascii=False, indent=2))
        return 0 if rec["ok"] and rec["flipped"] else 2
    host, ports = resolve_serve_args(sys.argv)
    serve(host, ports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
