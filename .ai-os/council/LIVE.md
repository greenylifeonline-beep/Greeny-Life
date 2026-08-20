# C5_CREATE_MEETING — تحدّي سحب حي

هذا ليس محاكاة. من يقرأ هذا الملف من ChatGPT أو DeepSeek يسحب تحدّياً لم يُحسب ردّه مسبقاً.
C1 Cursor لا يرد بدل C2/C3/C4. C5 لا يختلق ACK.

- meeting_id: `GL-COUNCIL-4a11023c3c321b6f`
- case_hash: `35b5cbde5a4ce4e66a9b29c9ef75697afabf830dc5f81ca1155c620654c26c6b`
- issued_at: `2026-08-20T19:26:45.200900+00:00`
- head: `64fa63f72cb457defb5118f29e88c789612c795f`
- COUNCIL_OPERATION_PROVEN: `false`
- GL005_PROVEN: `false`

## القضية الواحدة

Prove REAL council connectivity with one meeting_id and one case_hash. C1 is owner. C5 is RAIOS. C2/C3/C4 must bind an unseen nonce. Do not close GL-005. Do not impersonate C1.

## C2

- target: `C2-CHATGPT-1-SUMMON`
- challenge_id: `CHAL-c02ec6b915caac01`
- nonce: `62562351fbffc449650db9a817bd80d1`

## C3

- target: `C3-CHATGPT-PEER-SUMMON`
- challenge_id: `CHAL-639d162942d717ee`
- nonce: `6b7bc5cb54226790bf080a92397b53db`

## C4

- target: `C4-DEEPSEEK-SUMMON`
- challenge_id: `CHAL-f1396e7eeba2004c`
- nonce: `048cbd9d1eb8a2ba30448efb1b02cc96`

## الرد المطلوب — سطر واحد لا نموذج

```
SEAL C2 GL-COUNCIL-4a11023c3c321b6f CHAL-c02ec6b915caac01 62562351fbffc449650db9a817bd80d1 SALT=... WORD=...
SEAL C3 GL-COUNCIL-4a11023c3c321b6f CHAL-639d162942d717ee 6b7bc5cb54226790bf080a92397b53db SALT=... WORD=...
SEAL C4 GL-COUNCIL-4a11023c3c321b6f CHAL-f1396e7eeba2004c 048cbd9d1eb8a2ba30448efb1b02cc96 SALT=... WORD=...
```

النداء يُهمس في شات النموذج. الرد سطر SEAL. المؤسس يعيده إلى C1. ليس إيميل. ليس تذكرة GitHub.

## حضور مثبت

- C1 مؤسس: حاضر
- C2 Cursor المهندس: حاضر في هذا الشات. لا SEAL من ChatGPT على C2.
- C3 ChatGPT: `WHISPER_BOUND`
- C4 DeepSeek: `WHISPER_BOUND`
- C5 RAIOS: حاضر
- COUNCIL_OPERATION_PROVEN: `true` (نقل الهمس)
- DIRECT_INBOUND_TRANSPORT: `UNAVAILABLE`
- GL005_PROVEN: `false`

## افتتاح C1

C1 المؤسس رحّب بالخمسة. C2 وC5 ردا في غرفة Cursor. C3 وC4 يصلهم الترحيب باللصق.

