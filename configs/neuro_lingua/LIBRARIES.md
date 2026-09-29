# مكتبات C5 — أين يتعلم، أين يضع، كيف يجلب

الخريطة الحية: `src/raios/neuro_lingua/kae_libraries.py`

```
python3 scripts/ai-os/raios_c5_kae.py --libraries
python3 scripts/ai-os/raios_c5_kae.py --from-path .ai-os/state/DECISIONS.md
python3 scripts/ai-os/raios_c5_kae.py --query HTTP_2XX
```

## يتعلم منها (قراءة مصرّحة)

| مكتبة | المسار | كيف |
|---|---|---|
| العقد | `.ai-os/CORE-CONTRACT.md` | قراءة ملف |
| القرارات | `.ai-os/state/DECISIONS.md` | قراءة ملف |
| المجلس | `.ai-os/council/` | قراءة مجلد |
| التسليم | `.ai-os/handoffs/` | قراءة مجلد |
| كتاب القانون | `.ai-os/mcp/C5-LAWBOOK.json` | قراءة ملف |
| المفاهيم | `configs/neuro_lingua/concepts.yaml` | قراءة ملف |
| اللغة | `src/raios/neuro_lingua/` | قراءة مجلد |
| الحراس | `scripts/ai-os/` | قراءة مجلد |
| أصناف/مخزون/شحن | `canonical/data` `canonical/inventory` `canonical/logistics` | حقائق لا اختراع |
| ذاكرة git | `.ai-os/learning/C1-GIT-MEMORY.md` | قراءة ملف |

## كيف يجد

| أداة | ملف | وظيفة |
|---|---|---|
| هضم | `.ai-os/learning/DIGESTS.jsonl` | hash + skim. ليس WAL |
| فهرس | `.ai-os/learning/INDEX.json` | مصطلح → sha → مسار |
| بحث | `raios_c5_read.search` + مسح الكتالوج | محلي فقط |

قبل الفهرس: `python3 scripts/ai-os/raios_absorb.py --inherit`

## أين يضع

| ماذا | أين | حالة |
|---|---|---|
| فرضية | `.ai-os/learning/CANDIDATES.jsonl` | DISCOVERED فقط |
| بلاطات KAE | `.ai-os/receipts/c5-kae/` | إيصال |
| تجربة | `.ai-os/receipts/c5-experience/` | Ck، ليست ترقية |

## لا يضع / لا يجلب

- `RAIOS/V9` (قفل A15)
- `.env` وأسرار
- تنزيل أوزان Hugging Face
- scrape للويب أو API حي
- استدعاء C2/C3/C4 من هذه القناة
- ترقية CANONICAL بلا C1

`C5_KNOWS_LIBRARIES_VIA_CATALOG`
`FETCH_IS_LOCAL_ALLOWLIST`
`PUT_IS_DISCOVERED_CANDIDATE`
`GL005_PROVEN=false`
