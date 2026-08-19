import argparse, json, sys
from pathlib import Path
from datetime import datetime

ROOT=Path.cwd(); AI=ROOT/".ai-os"; ST=AI/"state"
def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def save(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def git(*a):
    native = ROOT / "_raios-a17-native-cortex"
    if str(native) not in sys.path:
        sys.path.insert(0, str(native))
    from ccee.process_kernel import encoding_safe_run
    obs = encoding_safe_run(["git", *map(str, a)], cwd=ROOT)
    text = ((obs.stdout or "") + (obs.stderr or "")).strip()
    return text
def need():
    if not AI.exists(): sys.exit("RAIOS not installed.")
def status(_):
    need(); pr=load(AI/"PROJECT.json"); cs=load(ST/"CURRENT-STATE.json"); t=load(ST/"TASKS.json")["tasks"]; l=load(ST/"LOCKS.json")["locks"]
    print("Project:",pr["project_name"]); print("Branch:",git("branch","--show-current")); print("HEAD:",git("rev-parse","HEAD"))
    print("Wave:",cs["active_wave"]); print("Goal:",cs["current_goal"])
    print("Active tasks:",sum(x.get("status") in ["READY","IN_PROGRESS","BLOCKED"] for x in t))
    print("Active locks:",sum(x.get("status")=="ACTIVE" for x in l))
    print("Dirty:","yes" if git("status","--short") else "no")
def snapshot(_):
    need(); x={"time":datetime.now().isoformat(),"branch":git("branch","--show-current"),"head":git("rev-parse","HEAD"),"status":git("status","--short").splitlines(),"tracked":len(git("ls-files").splitlines())}
    p=AI/"snapshots"/(datetime.now().strftime("%Y%m%d-%H%M%S")+".json"); save(p,x); print(p)
def task_add(a):
    d=load(ST/"TASKS.json")
    if any(x["id"]==a.id for x in d["tasks"]): sys.exit("Task exists.")
    d["tasks"].append({"id":a.id,"title":a.title,"objective":a.objective,"scope":a.scope.split(",") if a.scope else [],"dependencies":a.depends.split(",") if a.depends else [],"allowed_agents":a.agents.split(",") if a.agents else [],"validation":a.validation or "","status":"READY","claimed_by":None})
    save(ST/"TASKS.json",d); print("Added",a.id)
def task_claim(a):
    d=load(ST/"TASKS.json"); t=next((x for x in d["tasks"] if x["id"]==a.id),None)
    if not t: sys.exit("Task not found.")
    if t["allowed_agents"] and a.agent not in t["allowed_agents"]: sys.exit("Agent not allowed.")
    for dep in t["dependencies"]:
        dt=next((x for x in d["tasks"] if x["id"]==dep),None)
        if not dt or dt.get("status")!="DONE": sys.exit("Dependency incomplete: "+dep)
    t["status"]="IN_PROGRESS"; t["claimed_by"]=a.agent; save(ST/"TASKS.json",d); print("Claimed",a.id)
def task_complete(a):
    d=load(ST/"TASKS.json"); t=next((x for x in d["tasks"] if x["id"]==a.id),None)
    if not t: sys.exit("Task not found.")
    t["status"]="DONE"; t["evidence"]=a.evidence or ""; save(ST/"TASKS.json",d); print("Done",a.id)
def ov(a,b):
    a=a.rstrip("/*/"); b=b.rstrip("/*/")
    return a==b or a.startswith(b+"/") or b.startswith(a+"/")
def lock(a):
    d=load(ST/"LOCKS.json")
    for x in d["locks"]:
        if x.get("status")=="ACTIVE" and ov(x["scope"],a.scope): sys.exit(f"Conflict: {x['id']} {x['agent']} {x['scope']}")
    lid="LOCK-"+datetime.now().strftime("%Y%m%d%H%M%S")
    d["locks"].append({"id":lid,"task_id":a.task,"agent":a.agent,"scope":a.scope,"status":"ACTIVE"})
    save(ST/"LOCKS.json",d); print(lid)
def unlock(a):
    d=load(ST/"LOCKS.json"); f=False
    for x in d["locks"]:
        if x["id"]==a.id and x.get("status")=="ACTIVE": x["status"]="RELEASED"; f=True
    save(ST/"LOCKS.json",d)
    if not f: sys.exit("Lock not found.")
    print("Released",a.id)
def handoff(a):
    need(); p=AI/"handoffs"/f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{a.agent}-{a.task}.md"
    p.write_text(f"""# Handoff
- Agent: {a.agent}
- Task: {a.task}
- Status: {a.status}
- Files: {a.files or 'NONE'}
- Validation: {a.validation or 'NOT RECORDED'}
- Evidence: {a.evidence or 'NOT RECORDED'}
- Next: {a.next or 'NOT RECORDED'}
- Branch: {git('branch','--show-current')}
- HEAD: {git('rev-parse','HEAD')}
""",encoding="utf-8"); print(p)
p=argparse.ArgumentParser(); s=p.add_subparsers(dest="c",required=True)
q=s.add_parser("status"); q.set_defaults(f=status)
q=s.add_parser("snapshot"); q.set_defaults(f=snapshot)
q=s.add_parser("task-add")
for x in ["id","title","objective"]: q.add_argument("--"+x,required=True)
for x in ["scope","depends","agents","validation"]: q.add_argument("--"+x)
q.set_defaults(f=task_add)
q=s.add_parser("task-claim"); q.add_argument("--id",required=True); q.add_argument("--agent",required=True); q.set_defaults(f=task_claim)
q=s.add_parser("task-complete"); q.add_argument("--id",required=True); q.add_argument("--evidence"); q.set_defaults(f=task_complete)
q=s.add_parser("lock"); q.add_argument("--task",required=True); q.add_argument("--agent",required=True); q.add_argument("--scope",required=True); q.set_defaults(f=lock)
q=s.add_parser("unlock"); q.add_argument("--id",required=True); q.set_defaults(f=unlock)
q=s.add_parser("handoff")
for x in ["agent","task","status"]: q.add_argument("--"+x,required=True)
for x in ["files","validation","evidence","next"]: q.add_argument("--"+x)
q.set_defaults(f=handoff)
a=p.parse_args(); a.f(a)

