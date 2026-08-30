# جرد محركات الدمج — RAIOS

هذه الجلسة **C2**. C5 يسكن في git. الجرد DISCOVERED وليس CANONICAL. لم يُنفَّذ أي دمج.

- الرأس: `a7b986d808cadb8a7ece6a062d4dde4ac4a61483`
- ملفات باسم merge/engine بعد الاستبعاد: `51`
- مرشحو E3: `{'candidates': 265, 'deep': 112}`
- دمج نُفّذ الآن: `false`
- WAL كُتب: `false`
- GL005_PROVEN: `false`

## كيف نستفيد

- شغّل المسار الحي فقط: mind-fill → absorb/INDEX → KAE → NeuroLingua. أمر واحد: python3 scripts/ai-os/raios_c5_train.py
- لا تشغّل brain.py ولا خطط الأرشيف ولا JSON محركات EOS-PRODUCTION.
- لا تدمج تلقائيًا. A13 يقول automatic_merge=false.
- WAL المعرفي لا يُنقل ولا يُكتب هنا (A15). محوّل NeuroLingua ليس حافلة ثانية.
- سجل ENGINE_REGISTRY هو قائمة الحرّاس الكنسية. ملف اسمه engine في الأرشيف ليس قدرة حيّة.
- الاستفادة = ضغط المعرفة وإعادة الاستخدام، لا محرك دمج رقم 113.
- إغلاق GL-005 يبقى AUTHENTICATED_ORCHESTRATION_TASK ثم استيعاب Qwen/Granite مستقل ثم GL005.

## المحركات المسماة

| id | الحالة | المسار | ماذا يدمج | نسخ |
|---|---|---|---|---:|
| `mind-fill` | `LIVE` | `scripts/ai-os/raios_c5_mind_fill.py` | ملفات مصرّح بها → DIGESTS ثم INDEX | 0 |
| `absorb` | `LIVE` | `scripts/ai-os/raios_absorb.py` | ملفات كبيرة → تجزئة +skim في DIGESTS.jsonl | 0 |
| `index` | `LIVE` | `scripts/ai-os/raios_c5_index.py` | DIGESTS → INDEX.json postings | 0 |
| `kae` | `LIVE` | `src/raios/neuro_lingua/kae.py` | خرج مصرّح → بلاطات FACT/RULE/WHY/PROCEDURE ثم CANDIDATES DISCOVERED | 0 |
| `book` | `LIVE` | `scripts/ai-os/raios_c5_book.py` | حرّاس حيّة → EXPERIENCE.json | 0 |
| `neurolingua-speak` | `LIVE` | `src/raios/neuro_lingua` | ar-EG / ar-GULF / en / nb-NO كلام كتالوج حتمي | 0 |
| `nl-wal-adapter` | `ADAPTER` | `src/raios/neuro_lingua/wal.py` | بروتوكول NL فوق cognitive_event_bus | 0 |
| `cognitive-wal` | `PRIMARY_LOCKED_A15` | `RAIOS/V9/runtime/cognitive_event_bus.py` | أحداث تعلّم بـ fsync وevent_hash وإعادة تشغيل | 0 |
| `semantic-engine` | `REFERENCE_LOCKED_A15` | `RAIOS/V9/cognition/semantic/semantic_engine.py` | ثقة [0,1] ومسارات داخل المستودع — ليس دمج ملفات مكررة | 0 |
| `workflow-engine` | `CANONICAL_GATED` | `canonical/lib/workflowEngine.ts` | حالة طلب بيع + موافقة بشرية متميزة | 0 |
| `audit-engine` | `CANONICAL_OFFLINE` | `canonical/intelligence/intelligence/engines/audit-engine.ts` | مصادر منتج → نتائج تكرار/حقول ناقصة | 1 |
| `data-integrity-engine` | `CANONICAL_OFFLINE` | `canonical/intelligence/intelligence/engines/data-integrity-engine.ts` | ملفات canonical مقابل تكرار المعرّف/الـ slug | 0 |
| `controlled-runtime` | `CANONICAL_GATED` | `canonical/intelligence/runtime/controlled-runtime-orchestrator.ts` | طلب → حوكمة GL-DOS → تنفيذ محكوم | 0 |
| `task-orchestration` | `PRODUCT_UNPROVEN` | `lib/intelligence/task-orchestration.ts` | عقد مراجعة execution:false | 0 |
| `engine-registry` | `LIVE_INDEX` | `canonical/intelligence/intelligence/core/engine-registry.ts` | قائمة الحرّاس الحيّة فقط — النسخ التاريخية ليست قدرات | 0 |
| `a13-dedup` | `CERTIFY_NO_AUTO_MERGE` | `RAIOS/V9/runtime/a13_agent_capability_dedup_certification.py` | لا شيء تلقائيًا — automatic_merge=false | 0 |
| `brain-discover-merge` | `DO_NOT_RUN` | `brain.py` | يمسح intelligence/ وقد ينفّذ أدوات --analyze ويكتب tools_manifest.json | 0 |
| `e3-ledger` | `DISCOVERED_LEDGER` | `E3-ENGINE-DECISION-LEDGER.md` | 112 مرشحًا مصنّفًا قراءة فقط | 0 |
| `knowledge-merge-analysis` | `ARCHIVE_INFLATED` | `archive/old_folders/unified-intelligence/reports/architecture/phase-22/knowledge-merge-analysis-20260726-180626.json` | 34152 أثرًا على مسارات Windows — تضخيم جرد | 0 |
| `domain-merge-plan` | `ARCHIVE_POLLUTED` | `archive/old_folders/GREENY-LIFE-EOS/governance/domain-merge-plan-v1.json` | نطاقات EOS — الملف يلوّث بمسارات venv/torch | 0 |

## وصف كل محرك وكيف نستخدمه

### حقن العقل (`mind-fill`)

- الإنجليزي: C5 mind-fill
- الحالة: `LIVE` — موجود: `True`
- التشغيل: `python3 scripts/ai-os/raios_c5_mind_fill.py`
- الاستفادة: C5 يقرأ العقد والقرارات والمنتجات بلا WAL وبلا LangChain. هذا دمج معرفة بالضغط لا بالتراكم.

### الامتصاص (`absorb`)

- الإنجليزي: digest absorb
- الحالة: `LIVE` — موجود: `True`
- التشغيل: `python3 scripts/ai-os/raios_absorb.py`
- الاستفادة: يدمج المدخلات الضخمة في لحظات. لا يُفرَّغ في Cognitive WAL.

### الفهرس المقلوب (`index`)

- الإنجليزي: C5 inverted index
- الحالة: `LIVE` — موجود: `True`
- التشغيل: `python3 scripts/ai-os/raios_c5_index.py`
- الاستفادة: استرجاع محلي أسرع من embeddings غير محمّلة. إصابة الفهرس ليست إجابة معرفية كاملة.

### محرك توريق المعرفة (`kae`)

- الإنجليزي: Knowledge Assimilation Engine
- الحالة: `LIVE` — موجود: `True`
- التشغيل: `python3 scripts/ai-os/raios_c5_kae.py`
- الاستفادة: يعيد استخدام المعنى. ليس LightRAG وليس WAL ثانيًا وليس استخراج استدلال خفي.

### دورة الكتاب (`book`)

- الإنجليزي: C5 book cycle
- الحالة: `LIVE` — موجود: `True`
- التشغيل: `python3 scripts/ai-os/raios_c5_book.py`
- الاستفادة: يجمع تجربة التشغيل. التجربة ليست معرفة. لا يغلق GL-005.

### NeuroLingua كلام العملاء (`neurolingua-speak`)

- الإنجليزي: NeuroLingua speak
- الحالة: `LIVE` — موجود: `True`
- التشغيل: `python3 scripts/ai-os/raios_c5_train.py`
- الاستفادة: دمج لغات العملاء بدون استدعاء LLM (llm_calls=0). ليس دمج أوزان.

### محوّل WAL لـ NeuroLingua (`nl-wal-adapter`)

- الإنجليزي: ExistingCognitiveWALWriter
- الحالة: `ADAPTER` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: يمنع WAL ثانيًا. الدمج هنا محوّل لا حافلة جديدة. هذه الشريحة لا تكتب WAL (قفل A15).

### حافلة الأحداث المعرفية (`cognitive-wal`)

- الإنجليزي: cognitive event bus / Cognitive WAL
- الحالة: `PRIMARY_LOCKED_A15` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: سلطة التعلّم الوحيدة. لا تُنقل ولا تُكتب من هذه الشريحة (A15). ليست شاشة C5.

### المحرك الدلالي V9 (`semantic-engine`)

- الإنجليزي: V9 semantic engine
- الحالة: `REFERENCE_LOCKED_A15` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: قيد إبستيمي. لا تشغّله كمدمج أصول. لا تكتب V9 من هذه الشريحة.

### محرك سير الطلب (`workflow-engine`)

- الإنجليزي: EOSWorkflowEngine
- الحالة: `CANONICAL_GATED` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: دمج تشغيلي للطلب لا للمعرفة. يحتاج Prisma حيًا. ليس GL-005.

### محرك تدقيق المنتجات (`audit-engine`)

- الإنجليزي: canonical audit-engine
- الحالة: `CANONICAL_OFFLINE` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: يكشف التعارض قبل الدمج. لا يحذف. استخدمه قراءة قبل أي consolidation.
- نسخ أخرى: `archive/old_folders/GREENY-LIFE-EOS-PRODUCTION/platform/audit/audit-engine.json`

### محرك سلامة البيانات (`data-integrity-engine`)

- الإنجليزي: data-integrity-engine
- الحالة: `CANONICAL_OFFLINE` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: يمنع دمجًا يفسد master_products. ليس حذفًا تلقائيًا.

### المنسّق المحكوم (`controlled-runtime`)

- الإنجليزي: ControlledRuntimeOrchestrator
- الحالة: `CANONICAL_GATED` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: حدود تنفيذ المنتج. لا تخلطه بدمج الأرشيف. إثباته المنفصل ما زال مطلوبًا.

### عقد المهام (`task-orchestration`)

- الإنجليزي: task-orchestration
- الحالة: `PRODUCT_UNPROVEN` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: مسار GL-005 الحيّ عندما يوجد POST /api/tasks مصادق. الوحدة وحدها لا تثبت GL-005.

### سجل المحركات الحي (`engine-registry`)

- الإنجليزي: ENGINE_REGISTRY
- الحالة: `LIVE_INDEX` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: مصدر أسماء المحركات المعتمدة في الكود الكنسي. لا تضف أرشيف JSON كقدرة.

### Dedup قدرات الوكلاء A13 (`a13-dedup`)

- الإنجليزي: A13 agent capability dedup
- الحالة: `CERTIFY_NO_AUTO_MERGE` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: يفصل التكرار دون دمج هدّام. لا تشغّل دمج أصول الوكلاء.

### دامج ذكاء brain.py (`brain-discover-merge`)

- الإنجليزي: brain.py discover_and_merge_intelligence
- الحالة: `DO_NOT_RUN` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: لا تشغّله. استخرج أفكار التصنيف فقط عبر محوّل محكوم. أوضاع البناء/التنظيف/التطور محظورة.

### دفتر قرارات E3 (`e3-ledger`)

- الإنجليزي: E3 engine decision ledger
- الحالة: `DISCOVERED_LEDGER` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: خريطة KEEP/RECONNECT/DO_NOT_RUN. ليست دليل تشغيل. 45 عنصرًا placeholder.

### تحليل دمج المعرفة phase-22 (`knowledge-merge-analysis`)

- الإنجليزي: legacy knowledge-merge-analysis
- الحالة: `ARCHIVE_INFLATED` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: لا تنفّذ خطته. لا تعامل عدد الملفات كذكاء. اضغط الحيّ بدل إعادة المسح.

### خطة دمج النطاقات EOS (`domain-merge-plan`)

- الإنجليزي: domain-merge-plan-v1
- الحالة: `ARCHIVE_POLLUTED` — موجود: `True`
- التشغيل: `لا يُشغَّل من هذه الشريحة`
- الاستفادة: فاسد كسلطة نطاق. لا تدمجه. المصدر الحي للمنتجات canonical/data.

## النسخ حسب الطبقة

| طبقة | عدد ملفات merge/engine |
|---|---:|
| `archive` | 40 |
| `canonical` | 4 |
| `e3_recon` | 3 |
| `live_keeper` | 1 |
| `other` | 1 |
| `raios_v9` | 1 |
| `reports` | 1 |

عدد الملفات ليس ذكاءً. أرشيف EOS-PRODUCTION مليء بتقارير JSON اسمها engine وليست وقت تشغيل.

`GL005_PROVEN=false`

