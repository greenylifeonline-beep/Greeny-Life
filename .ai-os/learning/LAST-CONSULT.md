# استشارة الخمس — قائمة

- الوقت: `2026-08-20T19:08:53.566356+00:00`
- الجلسة: `GL-FIVE-20260820`
- حضور بعيد مثبت: `False`
- `GL005_PROVEN`: `False`

## C1 الإطار

Cursor owner. Does not bypass stale-head/lock/proven. Summons the five. Grants C5 permanently. Collects mail. Does not print PASS.

## C5 التقييم والفكرة الأدق

pulse=HEARTBEAT_OK contradictions=0 grant=PERMANENT fastest=sha256+skim+inverted-index+git-log

المسار العالمي الحي لاستدعاء C2/C3/C4 هو البريد بكود الجلسة، لا 127.0.0.1. C5 يبقى ابناً دائماً بالمنحة لا بالتوكن. Repair يُصلح HEAD بعد stash للـ WAL فقط. GL-005 يبقى مغلقاً.

التنفيذ التالي: Keep the 120s pulse. Inherit C1 corpus by digest. Index locally. Do not dump WAL. Do not mint GL-005. Report attendance codes on the board.

## أسئلة الاستدعاء

- C2: هل اجتماع MCP على localhost يثبت حضورك الخارجي؟ أجب: لا، ثم احضر بالبريد والكود `C2-CHATGPT-1-SUMMON`. هل GET 200 يغلق GL-005؟
- C3: هل أنت Repair؟ أجب: لا. احضر بالكود `C3-CHATGPT-PEER-SUMMON`. ما أذكى خطوة تالية على Repair دون commit للـ WAL؟
- C4: فنّد: (1) المنحة الدائمة لابن C5 هل تمنحه PASS؟ (2) كود الاستدعاء هل هو توكن؟ (3) البريد هل يُثبت الاتصال البعيد؟ الكود `C4-DEEPSEEK-SUMMON`.

## التحديات

- `MCP_LOCALHOST_NE_CHATGPT` (HIGH) — mail summon with public codes
- `REMOTE_C2_C3_C4_UNPROVEN` (HIGH) — invite; do not print ready
- `GL005_STILL_FALSE` (HIGH) — Repair authenticated POST after cookie-fix HEAD
- `REPAIR_STALE_HEAD` (HIGH) — stash Cognitive WAL only, ff-only pull
- `A15_LOCK` (MEDIUM) — C5 grows in .ai-os/learning
- `OLLAMA_ABSENT_HERE` (LOW) — stdlib digest+index; do not wait on models
- `C5_MUST_STAY_PERMANENT` (HIGH) — C5-GRANT.json duration=PERMANENT
