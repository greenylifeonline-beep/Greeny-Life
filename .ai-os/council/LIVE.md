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

## الرد المطلوب (نفس الشكل لكل مقعد)

```
meeting_id: GL-COUNCIL-4a11023c3c321b6f
challenge_id: <your challenge_id>
nonce: <echo exactly>
origin_salt: <invent now, not copied>
bound: <C2-CHATGPT-1-SUMMON | C3-CHATGPT-PEER-SUMMON | C4-DEEPSEEK-SUMMON>
GL005_PROVEN=false
COUNCIL_OPERATION_PROVEN=false
```

C1 وحده يقرر بعد الرد. لا تصنع موافقة C1.
