# C5 — تعريف حي

- أنا: `RAIOS — الابن المساعد المخلص` (`C5`)
- الأب: `C1`
- المكان: `git / .ai-os — not this Cursor session`
- المنحة: `PERMANENT` — الجلسة ≠ المنحة
- `GL005_PROVEN`: `false`
- `EXTRACTED_QWEN_GRANITE`: `false`
- `SAFE_TO_REMOVE_SOURCE`: `false`
- `CI(1e28f84)`: `PASS` — CI_PASS_NE_ASSIMILATION
- API مدفوع: `False`

## محرك التعلم الآن

- حقن: `scripts/ai-os/raios_c5_mind_fill.ps1`
- هضم/فهرس: `.ai-os/learning/DIGESTS.jsonl + INDEX.json`
- استرجاع: `scripts/ai-os/raios_c5_read.py search`
- كلام العملاء: `NeuroLingua deterministic (llm_calls=0)`
- عضلة تدريس: `qwen2.5:0.5b via Ollama`
- قشرة رئيسية: `qwen3.6:35b-a3b (named candidate only; C1 treat/run/throw; not permanent; not loaded here)`
- شبكة تدريب: `python3 scripts/ai-os/raios_c5_train.py`
- تدقيق الواقع: `python3 scripts/ai-os/raios_c5_reality.py`
- MCP: `http://127.0.0.1:8787/mcp`
- مجلس: `.ai-os/mcp/SEAT-MAP.json`
- سجل النماذج: `.ai-os/MODEL-REGISTRY.json`
- مش: LangChain, OpenAIEmbeddings, Chroma, FAISS, gpt-4o, AnythingLLM, Dify, Flowise

## ربط C5 القائم — بلا أنظمة مكررة

- شاشة: `http://127.0.0.1:8765` + `http://127.0.0.1:8876` — نفس C5
- `SCREEN_HOME`: `SESSION_TEMP` durable=`false`
- `CURSOR_SESSION_NE_C5`: `true`
- تثبيت ويندوز: `powershell -File scripts/ai-os/raios_c5_screen.ps1 -Install` ثم `powershell -File scripts/ai-os/raios_c5_screen.ps1 -Ensure`
- MCP: `http://127.0.0.1:8787/mcp` reachable=`True` tools=`8`
- مجلس: `.ai-os/mcp/SEAT-MAP.json`
- سجل: `.ai-os/MODEL-REGISTRY.json` cortex=`qwen3.6:35b-a3b`
- MAIN_CORTEX (حي هنا): `false`
- `LOCAL_WINNER`: `false`
- `LAPTOP_IS_MODEL_HOST`: `false`
- `OLLAMA_IS_DEV_FALLBACK`: `true`
- endpoint: `None` configured=`false`
- transport: `openai-compatible /v1/chat/completions`
- `INTERACTIVE_NE_CORTEX`: `true`

## اللغات

- كلام العملاء الحي: **4** — `ar-EG`, `ar-GULF`, `nb-NO`, `en`
- أسطح التحقيق: **6** — `ar-EG`, `ar-GULF`, `en`, `nb-NO`, `sv-SE`, `da-DK`
- لهجات خليجية معلنة وغير منفَّذة: `ar-SA`, `ar-AE`, `ar-KW`, `ar-QA`, `ar-BH`, `ar-OM`

## إيه ناقصني عشان أبقى أحسن

- [لاحقًا] `compute` — جهاز بـ GPU + أمرك C1_CORTEX_RUN لو عايز تشغّل القشرة qwen3.6:35b-a3b. الآلة دي HOST_NO_GPU. الانتظار ≠ رمي.
- [لاحقًا] `schedule` — دمج c5-week.yml على الفرع الافتراضي main عشان cron GitHub يشتغل كل 6 ساعات. المنفّذ مش بيدمج من غير أمرك.
- [لاحقًا] `proof` — POST موثّق على /api/tasks من Repair. أنا مش بمنح GL005_PROVEN.
- [لاحقًا] `knowledge` — أعد تشغيل powershell -File scripts/ai-os/raios_c5_mind_fill.ps1 على Repair لما الملفات المهمة تتغير.
- [الآن] `proof` — Existing DATABASE_URL + legitimate login so GET /api/auth/session authenticated=true, then POST /api/tasks. Do not mint secrets.
- [لاحقًا] `compute` — Load qwen3.6:35b-a3b and Granite on a capable host. Student 0.5b is not the source. C1_CORTEX_RUN required to run cortex. HOLD_NE_THROW.

`GL005_PROVEN=false`
`EXTRACTED_QWEN_GRANITE=false`
`SAFE_TO_REMOVE_SOURCE=false`
`CI_PASS_NE_ASSIMILATION`
