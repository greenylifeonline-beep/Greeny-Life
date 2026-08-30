# عزل Main Cortex — CASE-016

أخطر وأضعف نقطة في النظام. ليست العمود الفقري الحي.

`MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK`
`STUDENT_NE_MAIN_CORTEX`
`TINY_QWEN_NE_CORTEX_IDENTITY`

الهوية تبقى `qwen3.6:35b-a3b`. لا تُستبدل بنموذج صغير. الحاكم لا يقبلها على المسار الحي.

المسار الحي = NeuroLingua الحتمي.
Qwen الطالب المحلي (`qwen2.5:0.5b` عبر Ollama) عضلة تعليم فقط.

`python3 scripts/ai-os/raios_c5_qwen.py --generate`
`python3 scripts/ai-os/raios_c5_tools_audit.py`

`GL005_PROVEN=false`
