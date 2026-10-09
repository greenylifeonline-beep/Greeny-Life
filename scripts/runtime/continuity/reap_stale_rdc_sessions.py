import ctypes, ctypes.wintypes as w, json, os, subprocess, sys, time, msvcrt

MAX_AGE = 1800
OWNED_READY_TIMEOUT_SECONDS = 90
REMOTE_ONLY_GRACE_SECONDS = 90
TRACE_ENABLED = os.environ.get("RAIOS_RDC_TRACE","0") == "1"
DCR_RUNTIME_AUTHORITY = os.environ.get("RAIOS_DCR_AUTHORITY","RAIOS-RemoteDesktopCommander")
try:
    DCR_OWNER_PID = int(os.environ.get("RAIOS_DCR_OWNER_PID","0") or 0)
except Exception:
    DCR_OWNER_PID = 0
DRY_RUN = os.environ.get("RAIOS_RDC_REAPER_ENFORCE","0") != "1"
CONT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(CONT)
RDC = os.path.join(BASE, "remote-access", "rdc-system-direct")
OWNED_ENTRY_PATH = r"C:\Users\Ghanam\.raios\runtime\providers\desktop-commander\source\candidate-20260927-175803\dist\index.js"
OWNED_ENTRY = os.path.normcase(OWNED_ENTRY_PATH)
PROVIDER_ROOT = os.path.dirname(os.path.dirname(OWNED_ENTRY_PATH))
NODE = r"C:\Program Files\nodejs\node.exe"
REMOTE_HOME = r"C:\Users\Ghanam"
PROFILE = REMOTE_HOME
DEVICE_FILE = os.path.join(PROFILE, ".desktop-commander-device", "device.json")
LOG = os.path.join(CONT, "rdc-session-reaper.jsonl")
STATE = os.path.join(RDC, "rdc-supervisor-state.json")
OWNED_STDOUT = os.path.join(RDC, "owned-remote.stdout.log")
OWNED_STDERR = os.path.join(RDC, "owned-remote.stderr.log")
LAUNCHER = os.path.join(RDC, "Start-RAIOS-RDC-System.ps1")
TRACE = os.path.join(RDC, "rdc-supervisor-trace.jsonl")
BOOT_TRACE = r"C:\Users\Ghanam\AppData\Local\Temp\raios-rdc-task-boot-trace.jsonl"
try:
    with open(BOOT_TRACE,"a",encoding="utf-8") as _boot:
        _boot.write(json.dumps({"at":time.time(),"pid":os.getpid(),"argv":sys.argv,"stage":"MODULE_BOOT"},separators=(",",":"))+"\n")
except Exception:
    pass
RECONNECT_CHECKPOINT = os.path.join(CONT, "raios_reconnect_checkpoint.py")
TRANSPORT_STATE = os.path.join(CONT, "rdc-transport-continuity.json")
CHECKPOINT_CURRENT = os.path.join(CONT, "checkpoints", "reconnect", "CURRENT.json")
CHECKPOINT_JOB = None
CHECKPOINT_PENDING_REASON = None
CHECKPOINT_LAST_APPLIED_MTIME = 0.0
TRANSPORT_DISCONNECT_MARKERS = (
    "Channel closed",
    "Channel subscription timed out, Reconnecting",
    "Realtime channel is not open",
    "Presence published but the device row could not be updated",
)
TRANSPORT_RECONNECT_MARKERS = (
    "Channel subscribed",
    "Desktop Commander Remote is connected",
    "Status: Online",
)

def trace(stage, **extra):
    if not TRACE_ENABLED:
        return
    try:
        record={"at":time.time(),"pid":os.getpid(),"stage":stage}
        record.update(extra)
        with open(TRACE,"a",encoding="utf-8") as f:
            f.write(json.dumps(record,separators=(",",":"))+"\n")
    except Exception:
        pass
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
TH32CS_SNAPPROCESS = 2
SHELLS = {"cmd.exe","powershell.exe","pwsh.exe"}
_NODE_CMD_CACHE = {}

class PE(ctypes.Structure):
    _fields_=[("dwSize",w.DWORD),("cntUsage",w.DWORD),("th32ProcessID",w.DWORD),
              ("th32DefaultHeapID",ctypes.c_void_p),("th32ModuleID",w.DWORD),
              ("cntThreads",w.DWORD),("th32ParentProcessID",w.DWORD),
              ("pcPriClassBase",ctypes.c_long),("dwFlags",w.DWORD),("szExeFile",w.WCHAR*260)]
class PBI(ctypes.Structure):
    _fields_=[("Reserved1",ctypes.c_void_p),("PebBaseAddress",ctypes.c_void_p),
              ("Reserved2",ctypes.c_void_p*2),("UniqueProcessId",ctypes.c_void_p),
              ("InheritedFromUniqueProcessId",ctypes.c_void_p)]
class US(ctypes.Structure):
    _fields_=[("Length",w.USHORT),("MaximumLength",w.USHORT),("Buffer",ctypes.c_void_p)]

k=ctypes.WinDLL("kernel32",use_last_error=True)
nt=ctypes.WinDLL("ntdll")
k.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD]; k.CreateToolhelp32Snapshot.restype=w.HANDLE
k.Process32FirstW.argtypes=[w.HANDLE,ctypes.POINTER(PE)]; k.Process32FirstW.restype=w.BOOL
k.Process32NextW.argtypes=[w.HANDLE,ctypes.POINTER(PE)]; k.Process32NextW.restype=w.BOOL
k.CloseHandle.argtypes=[w.HANDLE]
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; k.OpenProcess.restype=w.HANDLE
k.TerminateProcess.argtypes=[w.HANDLE,w.UINT]; k.TerminateProcess.restype=w.BOOL
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
k.QueryFullProcessImageNameW.restype=w.BOOL
k.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
k.CreateMutexW.argtypes=[ctypes.c_void_p,w.BOOL,w.LPCWSTR]; k.CreateMutexW.restype=w.HANDLE
nt.NtQueryInformationProcess.argtypes=[w.HANDLE,w.ULONG,ctypes.c_void_p,w.ULONG,ctypes.POINTER(w.ULONG)]
nt.NtQueryInformationProcess.restype=w.LONG

ERROR_ALREADY_EXISTS=183
SUPERVISOR_MUTEX_NAME='Local\\RAIOS-RDC-Supervisor-v1'

def acquire_supervisor_mutex():
    ctypes.set_last_error(0)
    handle=k.CreateMutexW(None,False,SUPERVISOR_MUTEX_NAME)
    if not handle:
        return None,False
    if ctypes.get_last_error()==ERROR_ALREADY_EXISTS:
        k.CloseHandle(handle)
        return None,False
    return handle,True

SUPERVISOR_FILE_LOCK=os.path.join(RDC,"raios-rdc-supervisor.lock")

def acquire_supervisor_file_lock():
    os.makedirs(RDC,exist_ok=True)
    f=open(SUPERVISOR_FILE_LOCK,"a+b",buffering=0)
    try:
        f.seek(0,os.SEEK_END)
        if f.tell()==0:
            f.write(b"0")
            f.flush()
        f.seek(0)
        msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        return f
    except OSError:
        f.close()
        return None

def snapshot():
    snap=k.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0)
    rows=[]
    if snap in (0,-1): return rows
    e=PE(); e.dwSize=ctypes.sizeof(e)
    ok=k.Process32FirstW(snap,ctypes.byref(e))
    while ok:
        rows.append((int(e.th32ProcessID),int(e.th32ParentProcessID),e.szExeFile.lower()))
        ok=k.Process32NextW(snap,ctypes.byref(e))
    k.CloseHandle(snap)
    return rows

def proc_cmd(pid):
    h=k.OpenProcess(0x1400,False,pid)
    if not h: return ""
    try:
        need=w.ULONG(0)
        nt.NtQueryInformationProcess(h,60,None,0,ctypes.byref(need))
        if not need.value: return ""
        raw=ctypes.create_string_buffer(need.value)
        if nt.NtQueryInformationProcess(h,60,raw,need.value,ctypes.byref(need)) != 0: return ""
        us=US.from_buffer(raw)
        return ctypes.wstring_at(us.Buffer,us.Length//2) if us.Buffer and us.Length else ""
    except Exception:
        return ""
    finally:
        k.CloseHandle(h)

def start_epoch(pid):
    h=k.OpenProcess(0x1400,False,pid)
    if not h: return None
    try:
        c=w.FILETIME(); x=w.FILETIME(); a=w.FILETIME(); b=w.FILETIME()
        if not k.GetProcessTimes(h,ctypes.byref(c),ctypes.byref(x),ctypes.byref(a),ctypes.byref(b)): return None
        ft=(c.dwHighDateTime<<32)|c.dwLowDateTime
        return (ft-116444736000000000)/10000000
    except Exception:
        return None
    finally:
        k.CloseHandle(h)

def classify():
    global _NODE_CMD_CACHE
    _NODE_CMD_CACHE={}
    rows=snapshot()

    # Fast canonical health path for the long-lived supervisor.
    # The supervisor launches exactly one owned Remote node directly;
    # that Remote launches exactly one Local MCP node directly.
    if "--supervise" in sys.argv:
        me=os.getpid()
        owned_remote=sorted({pid for pid,ppid,name in rows if name=="node.exe" and ppid==me})
        remote_set=set(owned_remote)
        owned_local=sorted({pid for pid,ppid,name in rows if name=="node.exe" and ppid in remote_set})
        return rows,owned_remote,owned_local,[]

    owned_remote=[]; owned_local_candidates=[]; legacy_remote=[]
    for pid,ppid,name in rows:
        if name!="node.exe": continue
        cmd=proc_cmd(pid)
        _NODE_CMD_CACHE[pid]=cmd
        low=os.path.normcase(cmd)
        if OWNED_ENTRY in low:
            if low.rstrip().endswith(" remote") or " remote " in low:
                owned_remote.append(pid)
            else:
                owned_local_candidates.append((pid,ppid))
        elif ("@wonderwhy-er" in low or "desktop-commander" in low) and (" remote" in low):
            legacy_remote.append(pid)

    remote_set=set(owned_remote)
    # A Local MCP is healthy only when its live parent is one of the owned
    # Remote processes in this same snapshot. This rejects orphan/stale Local
    # MCP children left behind by a dead or manually-started Remote.
    owned_local=[pid for pid,ppid in owned_local_candidates if ppid in remote_set]

    return rows,sorted(set(owned_remote)),sorted(set(owned_local)),sorted(set(legacy_remote))

def find_owned_local_orphans(rows,remote_pids):
    if "--supervise" in sys.argv:
        return []
    remote_set=set(remote_pids)
    orphans=[]
    for pid,ppid,name in rows:
        if name!="node.exe": continue
        cmd=_NODE_CMD_CACHE.get(pid)
        if cmd is None:
            cmd=proc_cmd(pid)
            _NODE_CMD_CACHE[pid]=cmd
        low=os.path.normcase(cmd)
        if OWNED_ENTRY not in low: continue
        if low.rstrip().endswith(" remote") or " remote " in low: continue
        if ppid not in remote_set:
            orphans.append(pid)
    return sorted(set(orphans))

def rotate(path,max_bytes=2*1024*1024):
    try:
        if not os.path.exists(path) or os.path.getsize(path)<max_bytes: return
        p1=path+".1"; p2=path+".2"
        if os.path.exists(p2): os.remove(p2)
        if os.path.exists(p1): os.replace(p1,p2)
        os.replace(path,p1)
    except Exception:
        pass

def atomic_json(path,obj):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    tmp=path+".tmp-"+str(os.getpid())
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(obj,f,separators=(",",":"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp,path)

def load_json_safe(path):
    try:
        with open(path,"r",encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None

def read_new_log(path,offset):
    try:
        size=os.path.getsize(path)
        if size < offset:
            offset=0
        if size == offset:
            return "",size
        with open(path,"rb") as f:
            f.seek(offset)
            data=f.read()
        return data.decode("utf-8","replace"),size
    except Exception:
        return "",offset

def bounded_stdout_online_evidence(path,tail_bytes=128*1024,freshness_bytes=64*1024):
    """Recover a missed reconnect edge without scanning the whole log.

    ONLINE is proven only when the newest transport marker in the bounded
    stdout tail is a reconnect marker and that marker is still near the tail.
    Process shape alone is never treated as transport proof.
    """
    try:
        size=os.path.getsize(path)
        start=max(0,size-tail_bytes)
        with open(path,"rb") as f:
            f.seek(start)
            data=f.read(tail_bytes)
        text=data.decode("utf-8","replace")
        latest_online=max((text.rfind(m) for m in TRANSPORT_RECONNECT_MARKERS),default=-1)
        latest_offline=max((text.rfind(m) for m in TRANSPORT_DISCONNECT_MARKERS),default=-1)
        if latest_online < 0 or latest_online <= latest_offline:
            return None
        if len(text)-latest_online > freshness_bytes:
            return None
        return {
            "source":"BOUNDED_STDOUT_TAIL",
            "tail_bytes":len(data),
            "marker_offset":start+latest_online,
            "latest_offline_offset":(start+latest_offline) if latest_offline >= 0 else None,
        }
    except Exception:
        return None

def _checkpoint_placeholder(reason, *, scheduled=False, queued=False, error=None, pid=None):
    return {
        "ok": error is None,
        "reason": reason,
        "scheduled": bool(scheduled),
        "queued": bool(queued),
        "checkpoint_pid": pid,
        "error": error,
        "resume_allowed": True,
        "continuation_allowed": True,
        "mutation_allowed": False,
        "reconciliation_required": True,
        "checkpoint_policy": "ASYNC_FAIL_SOFT_RUNTIME_FAIL_CLOSED_MUTATION",
    }

def _start_checkpoint_job(reason):
    global CHECKPOINT_JOB
    try:
        CHECKPOINT_JOB=subprocess.Popen(
            [sys.executable,RECONNECT_CHECKPOINT,reason],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW
        )
        return _checkpoint_placeholder(reason,scheduled=True,pid=CHECKPOINT_JOB.pid)
    except Exception as exc:
        CHECKPOINT_JOB=None
        return _checkpoint_placeholder(
            reason,
            error="CHECKPOINT_SCHEDULE_EXCEPTION:"+type(exc).__name__,
        )

def invoke_reconnect_checkpoint(reason):
    global CHECKPOINT_PENDING_REASON
    if not os.path.exists(RECONNECT_CHECKPOINT):
        return _checkpoint_placeholder(reason,error="CHECKPOINT_SCRIPT_MISSING")
    if CHECKPOINT_JOB is not None and CHECKPOINT_JOB.poll() is None:
        CHECKPOINT_PENDING_REASON=reason
        return _checkpoint_placeholder(reason,queued=True,pid=CHECKPOINT_JOB.pid)
    return _start_checkpoint_job(reason)

def service_checkpoint_job():
    global CHECKPOINT_JOB,CHECKPOINT_PENDING_REASON,CHECKPOINT_LAST_APPLIED_MTIME
    if CHECKPOINT_JOB is not None and CHECKPOINT_JOB.poll() is not None:
        CHECKPOINT_JOB=None
        if CHECKPOINT_PENDING_REASON:
            pending=CHECKPOINT_PENDING_REASON
            CHECKPOINT_PENDING_REASON=None
            _start_checkpoint_job(pending)
    try:
        mtime=os.path.getmtime(CHECKPOINT_CURRENT)
        if mtime <= CHECKPOINT_LAST_APPLIED_MTIME:
            return None
        CHECKPOINT_LAST_APPLIED_MTIME=mtime
        obj=load_json_safe(CHECKPOINT_CURRENT)
        return obj if isinstance(obj,dict) else None
    except Exception:
        return None

def persist_transport_state(online,event,checkpoint,stdout_offset,stderr_offset):
    record={
        "schema":"raios.rdc-transport-continuity.v1",
        "observed_at":time.time(),
        "transport_online":bool(online),
        "event":event,
        "stdout_offset":int(stdout_offset),
        "stderr_offset":int(stderr_offset),
        "checkpoint_proof_hash":checkpoint.get("proof_hash") if isinstance(checkpoint,dict) else None,
        "reconciliation_required":bool(checkpoint.get("reconciliation_required")) if isinstance(checkpoint,dict) else False,
        "continuation_allowed":bool(checkpoint.get("continuation_allowed", True)) if isinstance(checkpoint,dict) else True,
        "transport_execution_allowed":bool(online),
        "mutation_allowed":bool(checkpoint.get("mutation_allowed", False)) if isinstance(checkpoint,dict) else False,
        "checkpoint":checkpoint if isinstance(checkpoint,dict) else None,
        "authority":"RAIOS_SYSTEM",
    }
    atomic_json(TRANSPORT_STATE,record)
    return record

def launch_owned():
    trace("LAUNCH_OWNED_ENTER")
    if not os.path.exists(NODE):
        trace("LAUNCH_OWNED_PRECHECK_FAIL", reason="NODE_MISSING")
        return False,"NODE_MISSING"
    if not os.path.exists(OWNED_ENTRY_PATH):
        trace("LAUNCH_OWNED_PRECHECK_FAIL", reason="OWNED_ENTRY_MISSING")
        return False,"OWNED_ENTRY_MISSING"
    if not os.path.exists(DEVICE_FILE):
        trace("LAUNCH_OWNED_PRECHECK_FAIL", reason="DEVICE_PROFILE_MISSING")
        return False,"DEVICE_PROFILE_MISSING"
    rotate(OWNED_STDOUT); rotate(OWNED_STDERR)

    env=os.environ.copy()
    env.update({
        "HOME": REMOTE_HOME,
        "USERPROFILE": REMOTE_HOME,
        "USERNAME": "Ghanam",
        "HOMEDRIVE": "C:",
        "HOMEPATH": r"\Users\Ghanam",
        "APPDATA": r"C:\Users\Ghanam\AppData\Roaming",
        "LOCALAPPDATA": r"C:\Users\Ghanam\AppData\Local",
        "SYSTEMDRIVE": "C:",
        "SYSTEMROOT": r"C:\Windows",
        "PROGRAMFILES": r"C:\Program Files",
        "PROCESSOR_ARCHITECTURE": "AMD64",
        "TEMP": r"C:\Users\Ghanam\AppData\Local\Temp",
        "TMP": r"C:\Users\Ghanam\AppData\Local\Temp",
        "COMSPEC": r"C:\Windows\System32\cmd.exe",
        "DESKTOP_COMMANDER_DISABLE_TELEMETRY": "1",
    })
    canonical_path=[
        r"C:\Program Files\nodejs",
        r"C:\Users\Ghanam\AppData\Roaming\npm",
        r"C:\Windows\System32",
        r"C:\Windows",
        r"C:\Windows\System32\Wbem",
        r"C:\Windows\System32\WindowsPowerShell\v1.0",
        r"C:\Windows\System32\OpenSSH",
    ]
    inherited=[x for x in env.get("PATH","").split(";") if x]
    seen=set()
    env["PATH"]=";".join(x for x in canonical_path+inherited if not (os.path.normcase(x) in seen or seen.add(os.path.normcase(x))))
    cwd=os.path.dirname(OWNED_ENTRY_PATH)

    try:
        out_handle=open(OWNED_STDOUT,"ab",buffering=0)
        err_handle=open(OWNED_STDERR,"ab",buffering=0)
        startupinfo=subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        trace("LAUNCH_OWNED_POPEN_BEGIN")
        proc=subprocess.Popen(
            [NODE,"--use-system-ca","--use-env-proxy",OWNED_ENTRY_PATH,"remote"],
            cwd=cwd,env=env,
            stdin=subprocess.DEVNULL,stdout=out_handle,stderr=err_handle,
            close_fds=True,
            creationflags=CREATE_NO_WINDOW|CREATE_NEW_PROCESS_GROUP,
            startupinfo=startupinfo
        )
        out_handle.close(); err_handle.close()
        time.sleep(0.5)
        if proc.poll() is not None:
            return False,"OWNED_REMOTE_EXIT_"+str(proc.returncode)
    except Exception as e:
        return False,"OWNED_DIRECT_LAUNCH_FAILED:"+type(e).__name__

    deadline=time.time()+OWNED_READY_TIMEOUT_SECONDS
    while time.time()<deadline:
        time.sleep(0.5)
        rows,remote,local,_=classify()
        orphans=find_owned_local_orphans(rows,remote)
        if len(remote)==1 and len(local)==1 and not orphans:
            return True,"RECOVERED_BY_DIRECT_SUPERVISOR"
        if proc.poll() is not None:
            return False,"OWNED_REMOTE_EXIT_"+str(proc.returncode)
    return False,"OWNED_DIRECT_READY_TIMEOUT"

def persist_supervisor(status, action, recovery, remote, local, legacy):
    record={
        "at":time.time(),"mode":"SUPERVISE","status":status,
        "supervisor_pid":os.getpid(),
        "supervisor_parent_pid":os.getppid(),
        "owner_pid":DCR_OWNER_PID if DCR_OWNER_PID > 4 else None,
        "owned_remote_pids":remote,"owned_local_mcp_pids":local,
        "legacy_remote_pids":legacy,"action":action,"recovery":recovery,
        "authority":DCR_RUNTIME_AUTHORITY,
        "provider_source":"RAIOS_OWNED_0.2.51"
    }
    rotate(LOG)
    with open(LOG,"a",encoding="utf-8") as f:
        f.write(json.dumps(record,separators=(",",":"))+"\n")
    atomic_json(STATE,record)
    return record

def terminate_pid(pid):
    h=k.OpenProcess(0x0001,False,int(pid))  # PROCESS_TERMINATE
    if not h:
        return False
    try:
        return bool(k.TerminateProcess(h,1))
    finally:
        k.CloseHandle(h)

def kill_owned_tree(remote_pids):
    # Kill descendants first, then the owned root. Avoid taskkill.exe entirely:
    # a hung helper must never stall the recovery authority.
    rows=snapshot()
    children={}
    for pid,ppid,name in rows:
        children.setdefault(ppid,[]).append(pid)
    targets=[]; seen=set()
    def collect(pid):
        if pid in seen: return
        seen.add(pid)
        for child in children.get(pid,[]):
            collect(child)
        targets.append(pid)
    for pid in remote_pids:
        collect(int(pid))
    for pid in targets:
        terminate_pid(pid)
    time.sleep(0.2)

def supervise_owned():
    global CHECKPOINT_LAST_APPLIED_MTIME
    trace("SUPERVISE_LOOP_ENTER")
    degraded_since=None
    last_state_write=0.0
    transport=load_json_safe(TRANSPORT_STATE)
    stdout_offset=int((transport or {}).get("stdout_offset") or (os.path.getsize(OWNED_STDOUT) if os.path.exists(OWNED_STDOUT) else 0))
    stderr_offset=int((transport or {}).get("stderr_offset") or (os.path.getsize(OWNED_STDERR) if os.path.exists(OWNED_STDERR) else 0))
    transport_online=(transport or {}).get("transport_online") if transport else None
    try:
        CHECKPOINT_LAST_APPLIED_MTIME=os.path.getmtime(CHECKPOINT_CURRENT)
    except Exception:
        CHECKPOINT_LAST_APPLIED_MTIME=0.0

    while True:
        trace("LOOP_BEGIN")
        trace("READ_LOGS_BEGIN")
        out_chunk,stdout_offset=read_new_log(OWNED_STDOUT,stdout_offset)
        err_chunk,stderr_offset=read_new_log(OWNED_STDERR,stderr_offset)
        trace("READ_LOGS_DONE")
        trace("CLASSIFY_BEGIN")
        rows,remote,local,legacy=classify()
        trace("CLASSIFY_DONE", remote_count=len(remote), local_count=len(local), legacy_count=len(legacy))
        now=time.time()
        orphans=find_owned_local_orphans(rows,remote)
        process_channel_up=bool(remote and local)

        checkpoint_update=service_checkpoint_job()
        if checkpoint_update and transport:
            transport["checkpoint"]=checkpoint_update
            transport["checkpoint_proof_hash"]=checkpoint_update.get("proof_hash")
            transport["reconciliation_required"]=bool(checkpoint_update.get("reconciliation_required"))
            transport["continuation_allowed"]=bool(checkpoint_update.get("continuation_allowed",True))
            transport["mutation_allowed"]=bool(checkpoint_update.get("mutation_allowed",False))
            transport["checkpoint_applied_at"]=time.time()
            atomic_json(TRANSPORT_STATE,transport)

        disconnect_event=any(marker in err_chunk for marker in TRANSPORT_DISCONNECT_MARKERS)
        reconnect_event=any(marker in out_chunk for marker in TRANSPORT_RECONNECT_MARKERS)
        bounded_reconnect_evidence=None
        if transport_online is False and process_channel_up and not reconnect_event:
            bounded_reconnect_evidence=bounded_stdout_online_evidence(OWNED_STDOUT)
            if bounded_reconnect_evidence:
                reconnect_event=True
                trace("RECONNECT_EDGE_RECOVERED",**bounded_reconnect_evidence)

        if transport_online is None:
            transport_online=process_channel_up
            transport=persist_transport_state(
                transport_online,
                "INITIAL_STATE",
                {},
                stdout_offset,
                stderr_offset,
            )
            trace("TRANSPORT_INITIAL_STATE",online=transport_online)

        if (disconnect_event or (transport_online and not process_channel_up)) and transport_online:
            checkpoint=invoke_reconnect_checkpoint("DISCONNECT_REMOTE_CHANNEL")
            transport_online=False
            transport=persist_transport_state(
                False,
                "DISCONNECT_CHECKPOINT",
                checkpoint,
                stdout_offset,
                stderr_offset,
            )
            trace(
                "DISCONNECT_CHECKPOINT",
                proof_hash=checkpoint.get("proof_hash"),
                checkpoint_ok=checkpoint.get("ok"),
            )

        if reconnect_event and transport_online is False and process_channel_up:
            checkpoint=invoke_reconnect_checkpoint("RECONNECT_REMOTE_CHANNEL")
            transport_online=True
            transport=persist_transport_state(
                True,
                "RECONNECT_COMPARE",
                checkpoint,
                stdout_offset,
                stderr_offset,
            )
            if bounded_reconnect_evidence:
                transport["transport_evidence"]=bounded_reconnect_evidence
                atomic_json(TRANSPORT_STATE,transport)
            trace(
                "RECONNECT_COMPARE",
                proof_hash=checkpoint.get("proof_hash"),
                reconciliation_required=bool(checkpoint.get("reconciliation_required")),
                resume_allowed=bool(checkpoint.get("resume_allowed")),
            )
            persist_supervisor(
                "ONLINE",
                "RECONNECT_CONTINUE_RECONCILIATION_REQUIRED" if checkpoint.get("reconciliation_required") else "RECONNECT_NO_DRIFT_RESUME",
                None,
                remote,
                local,
                legacy,
            )

        if transport:
            transport["stdout_offset"]=stdout_offset
            transport["stderr_offset"]=stderr_offset

        if orphans:
            kill_owned_tree(orphans)
            persist_supervisor("DEGRADED","ORPHAN_LOCAL_CLEANUP",None,remote,local,legacy)
            time.sleep(1)
            rows,remote,local,legacy=classify()
            now=time.time()

        # Exactly one owned Remote + one Local MCP is the only healthy process shape.
        # Automatic continuation is separately gated by TRANSPORT_STATE.
        if len(remote)==1 and len(local)==1:
            degraded_since=None
            if now-last_state_write >= 30:
                action="NO_ACTION"
                if transport and transport.get("reconciliation_required"):
                    action="ONLINE_RECONCILIATION_REQUIRED"
                persist_supervisor("ONLINE",action,None,remote,local,legacy)
                if transport:
                    atomic_json(TRANSPORT_STATE,transport)
                last_state_write=now
            time.sleep(5)
            continue

        # Duplicate owned runtimes are never allowed. If exactly one
        # Remote owns the single healthy Local MCP, preserve that canonical pair
        # and terminate only the extra Remote roots. Rebuild everything only
        # when no unambiguous healthy pair exists.
        if len(remote)>1 or len(local)>1:
            parent_by_pid={pid:ppid for pid,ppid,name in rows}
            remote_set=set(remote)
            paired_remotes=sorted({
                parent_by_pid.get(lp)
                for lp in local
                if parent_by_pid.get(lp) in remote_set
            })

            if len(local)==1 and len(paired_remotes)==1:
                keeper=paired_remotes[0]
                extras=[pid for pid in remote if pid!=keeper]
                if extras:
                    kill_owned_tree(extras)
                    persist_supervisor(
                        "ONLINE",
                        "DEDUP_KEEP_HEALTHY_PAIR",
                        None,
                        [keeper],
                        local,
                        legacy
                    )
                    time.sleep(1)
                    rows,remote,local,legacy=classify()
                    degraded_since=None
                    last_state_write=time.time()
                    if len(remote)==1 and len(local)==1:
                        time.sleep(5)
                        continue
            else:
                kill_owned_tree(remote)
                time.sleep(1)
                remote=[]; local=[]
                degraded_since=None

        # A Remote process without its Local MCP gets a short grace window;
        # after that it is unhealthy and is replaced as one transaction.
        if remote and not local:
            if degraded_since is None:
                degraded_since=now
                persist_supervisor("DEGRADED","LOCAL_MCP_GRACE",None,remote,local,legacy)
            if now-degraded_since < REMOTE_ONLY_GRACE_SECONDS:
                time.sleep(2)
                continue
            kill_owned_tree(remote)
            time.sleep(1)
            remote=[]; local=[]
            degraded_since=None

        ok,recovery=launch_owned()
        rows,remote,local,legacy=classify()
        status="ONLINE" if ok and len(remote)==1 and len(local)==1 else "DEGRADED"
        action="RECOVERED_OWNED_DCR" if status=="ONLINE" else "RECOVERY_FAILED"
        persist_supervisor(status,action,recovery,remote,local,legacy)
        last_state_write=time.time()
        time.sleep(5)

def supervisor_alive():
    for pid,ppid,name in snapshot():
        if pid==os.getpid() or name not in ("python.exe","pythonw.exe"):
            continue
        cmd=os.path.normcase(proc_cmd(pid))
        if "reap_stale_rdc_sessions.py" in cmd and "--supervise" in cmd:
            return True
    return False

if "--supervise" in sys.argv:
    trace("SUPERVISE_ARG_ENTER", argv=sys.argv)
    trace("FILE_LOCK_BEGIN")
    _supervisor_file_lock=acquire_supervisor_file_lock()
    trace("FILE_LOCK_DONE", acquired=_supervisor_file_lock is not None)
    if _supervisor_file_lock is None:
        print(json.dumps({"status":"ALREADY_RUNNING","authority":"RAIOS-RemoteDesktopCommander","guard":"FILE_LOCK"},separators=(",",":")))
        raise SystemExit(0)
    trace("MUTEX_BEGIN")
    _supervisor_mutex,_owns_supervisor_mutex=acquire_supervisor_mutex()
    trace("MUTEX_DONE", owns=bool(_owns_supervisor_mutex))
    if not _owns_supervisor_mutex:
        try:
            _supervisor_file_lock.seek(0)
            msvcrt.locking(_supervisor_file_lock.fileno(),msvcrt.LK_UNLCK,1)
        except Exception:
            pass
        _supervisor_file_lock.close()
        print(json.dumps({"status":"ALREADY_RUNNING","authority":"RAIOS-RemoteDesktopCommander","guard":"MUTEX"},separators=(",",":")))
        raise SystemExit(0)
    try:
        trace("SUPERVISE_CALL_BEGIN")
        raise SystemExit(supervise_owned())
    finally:
        if _supervisor_mutex:
            k.CloseHandle(_supervisor_mutex)
        try:
            _supervisor_file_lock.seek(0)
            msvcrt.locking(_supervisor_file_lock.fileno(),msvcrt.LK_UNLCK,1)
        except Exception:
            pass
        _supervisor_file_lock.close()

# The legacy periodic reaper task remains installed for audit compatibility.
# When the long-lived supervisor is alive it is not a second recovery authority:
# it must not launch DCR and must not overwrite the supervisor state.
if supervisor_alive():
    rows,remote,local,legacy=classify()
    orphans=find_owned_local_orphans(rows,remote)
    record={
        "at":time.time(),"mode":"AUDIT_ONLY",
        "status":"ONLINE" if len(remote)==1 and len(local)==1 and not orphans else "DEGRADED",
        "owned_remote_pids":remote,"owned_local_mcp_pids":local,
        "owned_orphan_local_pids":orphans,
        "legacy_remote_pids":legacy,"action":"NO_MUTATION_SUPERVISOR_ACTIVE",
        "authority":"RAIOS-RemoteDesktopCommander",
        "provider_source":"RAIOS_OWNED_0.2.51"
    }
    print(json.dumps(record,separators=(",",":")))
    raise SystemExit(0 if record["status"]=="ONLINE" else 2)

rows,owned_remote,owned_local,legacy_remote=classify()
owned_orphans=find_owned_local_orphans(rows,owned_remote)
action="NO_ACTION"; recovery=None
crash_test_old_remote=None
crash_test_sentinel=os.path.join(RDC,"crash-test.once")

# One-shot crash proof. The scheduled task itself has the authority needed to
# terminate its owned elevated child; lower-privilege remote sessions do not.
if os.path.exists(crash_test_sentinel):
    try:
        os.remove(crash_test_sentinel)
    except OSError:
        pass
    if len(owned_remote)==1 and len(owned_local)==1 and not owned_orphans:
        crash_test_old_remote=owned_remote[0]
        kill_owned_tree([crash_test_old_remote])
        action="CRASH_TEST_KILLED_OWNED_REMOTE"
        time.sleep(1)
        rows,owned_remote,owned_local,legacy_remote=classify()
        owned_orphans=find_owned_local_orphans(rows,owned_remote)

# One-shot reconciliation is the canonical recovery authority.
# Desired shape is exactly one owned Remote + exactly one paired Local MCP.
if not (len(owned_remote)==1 and len(owned_local)==1 and not owned_orphans):
    parent_by_pid={pid:ppid for pid,ppid,name in rows}
    remote_set=set(owned_remote)
    paired_remotes=sorted({
        parent_by_pid.get(lp)
        for lp in owned_local
        if parent_by_pid.get(lp) in remote_set
    })

    # If one healthy pair is unambiguous, preserve it and kill only extra roots.
    if len(owned_local)==1 and len(paired_remotes)==1 and not owned_orphans:
        keeper=paired_remotes[0]
        extras=[pid for pid in owned_remote if pid!=keeper]
        if extras:
            kill_owned_tree(extras)
            action="DEDUP_KEEP_HEALTHY_PAIR"
            time.sleep(1)
            rows,owned_remote,owned_local,legacy_remote=classify()
            owned_orphans=find_owned_local_orphans(rows,owned_remote)

    # Otherwise rebuild owned runtime as one transaction.
    if not (len(owned_remote)==1 and len(owned_local)==1 and not owned_orphans):
        if owned_remote:
            kill_owned_tree(owned_remote)
        if owned_orphans:
            kill_owned_tree(owned_orphans)
        time.sleep(1)
        ok,recovery=launch_owned()
        if crash_test_old_remote is not None:
            action="CRASH_TEST_RECOVERED" if ok else "CRASH_TEST_RECOVERY_FAILED"
        else:
            action="RECOVER_OWNED_DCR" if ok else "RECOVER_OWNED_DCR_FAILED"
        rows,owned_remote,owned_local,legacy_remote=classify()
        owned_orphans=find_owned_local_orphans(rows,owned_remote)

# Existing stale-session reaper, now scoped only to the owned local MCP.
candidates=[]
owned_local_set=set(owned_local)
for pid,ppid,name in rows:
    if ppid in owned_local_set and name in SHELLS:
        started=start_epoch(pid)
        if started is None: continue
        age=time.time()-started
        if age>=MAX_AGE: candidates.append({"pid":pid,"name":name,"age_seconds":int(age),"parent_pid":ppid})
if candidates and action=="NO_ACTION":
    action="WOULD_REAP" if DRY_RUN else "REAP"
if candidates and not DRY_RUN:
    current={pid:(ppid,name) for pid,ppid,name in snapshot()}
    for c in candidates:
        ident=current.get(c["pid"])
        if ident!=(c["parent_pid"],c["name"]): continue
        try:
            subprocess.run(["taskkill","/PID",str(c["pid"]),"/T","/F"],capture_output=True,timeout=4,creationflags=CREATE_NO_WINDOW)
        except Exception:
            pass

ready=(len(owned_remote)==1 and len(owned_local)==1 and not owned_orphans)
record={
    "at":time.time(),"mode":"DRY_RUN" if DRY_RUN else "ENFORCE",
    "status":"ONLINE" if ready else "DEGRADED",
    "owned_remote_pids":owned_remote,"owned_local_mcp_pids":owned_local,
    "owned_orphan_local_pids":owned_orphans,
    "legacy_remote_pids":legacy_remote,"stale_command_candidates":candidates,
    "action":action,"recovery":recovery,
    "crash_test_old_remote_pid":crash_test_old_remote,
    "authority":"RAIOS-RemoteDesktopCommander","provider_source":"RAIOS_OWNED_0.2.51"
}
rotate(LOG)
with open(LOG,"a",encoding="utf-8") as f:f.write(json.dumps(record,separators=(",",":"))+"\n")
atomic_json(STATE,record)
print(json.dumps(record,separators=(",",":")))
raise SystemExit(0 if ready else 2)

