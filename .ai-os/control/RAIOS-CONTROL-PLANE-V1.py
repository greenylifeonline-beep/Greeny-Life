from __future__ import annotations
import hashlib, json, os, subprocess, sys, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT=Path(os.getenv("RAIOS_CANONICAL_REPO",Path(__file__).resolve().parents[2])).resolve()
if ROOT.name.casefold()=="greeny-life-repair" or not (ROOT/".git").exists():
    raise SystemExit(f"NON_CANONICAL_ROOT::{ROOT}")
CTRL=ROOT/".ai-os"/"control"; STATE=ROOT/".ai-os"/"state"/"command-fabric"
INBOX=STATE/"inbox"; OUTBOX=STATE/"outbox"; RECEIPTS=ROOT/".ai-os"/"receipts"/"command-fabric"
for p in (STATE,INBOX,OUTBOX,RECEIPTS): p.mkdir(parents=True,exist_ok=True)
REG=STATE/"WORKER-REGISTRY.json"; LEASES=STATE/"leases"; LEASES.mkdir(exist_ok=True)
HEAD=lambda: subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
now=lambda: datetime.now(timezone.utc)
def iso(t=None): return (t or now()).isoformat()
def load(p,default=None):
    try: return json.loads(p.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError,json.JSONDecodeError): return default
def atomic(p,obj):
    tmp=p.with_suffix(p.suffix+".tmp"); raw=json.dumps(obj,indent=2,ensure_ascii=False)+"\n"
    tmp.write_text(raw,encoding="utf-8"); os.replace(tmp,p)
    return hashlib.sha256(p.read_bytes()).hexdigest()
def parse_ts(v):
    try: return datetime.fromisoformat(v.replace("Z","+00:00"))
    except Exception: return datetime.min.replace(tzinfo=timezone.utc)
def heartbeat(worker_id,ttl=90):
    reg=load(REG,{"schema":"raios.worker-registry.v2","workers":[]}); t=now(); found=False
    for w in reg["workers"]:
        if w.get("worker_id")==worker_id:
            w.update(heartbeat=iso(t),lease_expires_at=iso(t+timedelta(seconds=ttl)),liveness="LIVE"); found=True
    if not found: raise SystemExit(f"UNKNOWN_WORKER::{worker_id}")
    reg.update(head=HEAD(),generated_at=iso(t)); atomic(REG,reg); return reg
def health(stale_after=120):
    reg=load(REG,{"workers":[]}); t=now(); result=[]
    for w in reg.get("workers",[]):
        age=(t-parse_ts(w.get("heartbeat",""))).total_seconds(); expired=t>=parse_ts(w.get("lease_expires_at",""))
        state="STALE" if age>stale_after or expired else "LIVE"
        result.append({"worker_id":w.get("worker_id"),"state":state,"age_seconds":round(age,3),"lease_expired":expired})
    return result
def active_lease(scope):
    t=now()
    for p in LEASES.glob("*.json"):
        x=load(p,{})
        if x.get("scope")==scope and x.get("state")=="ACTIVE" and parse_ts(x.get("expires_at",""))>t: return x
    return None
def acquire(owner,scope,ttl=120):
    existing=active_lease(scope)
    if existing and existing.get("owner")!=owner: raise SystemExit(f"LEASE_CONFLICT::{existing['owner']}::{scope}")
    t=now(); epoch=int(t.timestamp()*1_000_000); lid=f"L-{epoch}-{uuid.uuid4().hex[:8]}"
    x={"schema":"raios.write-lease.v2","lease_id":lid,"fence_token":epoch,"owner":owner,"scope":scope,"head":HEAD(),"issued_at":iso(t),"expires_at":iso(t+timedelta(seconds=ttl)),"state":"ACTIVE","fail_closed":True}
    atomic(LEASES/f"{lid}.json",x); return x
def assert_write(owner,scope,lease_id,fence_token):
    x=load(LEASES/f"{lease_id}.json",{})
    checks=[x.get("owner")==owner,x.get("scope")==scope,x.get("state")=="ACTIVE",x.get("fence_token")==int(fence_token),parse_ts(x.get("expires_at",""))>now(),x.get("head")==HEAD()]
    if not all(checks): raise SystemExit("WRITE_FENCE_REJECTED")
    return True
def send(sender,target,kind,payload,external=False):
    mid=f"MSG-{int(now().timestamp()*1_000_000)}-{uuid.uuid4().hex[:8]}"
    msg={"schema":"raios.message.v1","message_id":mid,"correlation_id":payload.get("correlation_id",mid),"sender":sender,"target":target,"kind":kind,"channel":"EXTERNAL_GATEWAY" if external else "INTERNAL_BUS","payload":payload,"created_at":iso(),"head":HEAD(),"ack_required":True}
    h=atomic(INBOX/f"{mid}.json",msg); atomic(RECEIPTS/f"{mid}.send.json",{"receipt_id":mid,"message_id":mid,"RECEIPT_ID_EQUALS_MESSAGE_ID":True,"sha256":h,"event":"SENT","at":iso()}); return msg
def ack(mid,actor,status="ACKNOWLEDGED"):
    src=INBOX/f"{mid}.json"; msg=load(src)
    if not msg: raise SystemExit("MESSAGE_NOT_FOUND")
    a={"schema":"raios.message-ack.v1","receipt_id":mid,"message_id":mid,"RECEIPT_ID_EQUALS_MESSAGE_ID":True,"actor":actor,"status":status,"at":iso(),"head":HEAD()}
    atomic(OUTBOX/f"{mid}.{actor}.ack.json",a); atomic(RECEIPTS/f"{mid}.{actor}.ack.receipt.json",a); return a
def watchdog():
    hs=health(); stale=[x for x in hs if x["state"]!="LIVE"]
    report={"schema":"raios.watchdog.v1","at":iso(),"head":HEAD(),"workers":hs,"stale_workers":stale,"fail_closed":bool(stale)}
    atomic(STATE/"WATCHDOG-STATUS.json",report); return report
def main(a):
    if not a: raise SystemExit("COMMAND_REQUIRED")
    c=a[0]
    if c=="heartbeat": out=heartbeat(a[1],int(a[2]) if len(a)>2 else 90)
    elif c=="health": out=health()
    elif c=="watchdog": out=watchdog()
    elif c=="acquire": out=acquire(a[1],a[2],int(a[3]) if len(a)>3 else 120)
    elif c=="assert-write": out={"allowed":assert_write(a[1],a[2],a[3],a[4])}
    elif c=="send":
        payload={"text":a[4]}
        if len(a)>6: payload["correlation_id"]=a[6]
        out=send(a[1],a[2],a[3],payload,len(a)>5 and a[5]=="external")
    elif c=="ack": out=ack(a[1],a[2])
    else: raise SystemExit(f"UNKNOWN_COMMAND::{c}")
    print(json.dumps(out,ensure_ascii=False))
if __name__=="__main__": main(sys.argv[1:])
