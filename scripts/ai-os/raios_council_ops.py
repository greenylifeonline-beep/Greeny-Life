#!/usr/bin/env python3
"""CLI for canonical RAIOS council operations."""
import argparse, json
from pathlib import Path
from raios.council_ops import CouncilOperations

def obj(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
p=argparse.ArgumentParser(prog="RAIOS-COUNCIL")
p.add_argument("--repo",default="."); p.add_argument("--runtime")
s=p.add_subparsers(dest="command",required=True)
for name in ("check-in","check-out"):
 q=s.add_parser(name); q.add_argument("--seat",required=True); q.add_argument("--auth-evidence",required=True); q.add_argument("--idempotency-key",required=True)
s.choices["check-out"].add_argument("--handoff-receipt")
q=s.add_parser("claim"); q.add_argument("--seat",required=True); q.add_argument("--task",required=True); q.add_argument("--auth-evidence",required=True); q.add_argument("--idempotency-key",required=True)
q=s.add_parser("handoff"); q.add_argument("--from-seat",required=True); q.add_argument("--to-seat",required=True); q.add_argument("--task",required=True); q.add_argument("--auth-evidence",required=True); q.add_argument("--idempotency-key",required=True); q.add_argument("--evidence",action="append",default=[])
q=s.add_parser("message"); q.add_argument("--from-seat",required=True); q.add_argument("--to-seat",required=True); q.add_argument("--task",required=True); q.add_argument("--text",required=True); q.add_argument("--auth-evidence",required=True); q.add_argument("--idempotency-key",required=True)
s.add_parser("audit")
a=p.parse_args(); op=CouncilOperations(Path(a.repo),Path(a.runtime) if a.runtime else None)
if a.command=="check-in": out=op.check_in(seat=a.seat,auth=obj(a.auth_evidence),idem=a.idempotency_key)
elif a.command=="check-out": out=op.check_out(seat=a.seat,auth=obj(a.auth_evidence),idem=a.idempotency_key,handoff_receipt=a.handoff_receipt)
elif a.command=="claim": out=op.claim(seat=a.seat,task_id=a.task,auth=obj(a.auth_evidence),idem=a.idempotency_key)
elif a.command=="handoff": out=op.handoff(from_seat=a.from_seat,to_seat=a.to_seat,task_id=a.task,auth=obj(a.auth_evidence),idem=a.idempotency_key,evidence=a.evidence)
elif a.command=="message": out=op.message(from_seat=a.from_seat,to_seat=a.to_seat,task_id=a.task,text=a.text,auth=obj(a.auth_evidence),idem=a.idempotency_key)
else: out=op.audit()
print(json.dumps(out,indent=2,ensure_ascii=False,sort_keys=True))
