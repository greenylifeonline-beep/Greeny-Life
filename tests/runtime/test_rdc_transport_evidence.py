import ast, os, tempfile
from pathlib import Path

MODULE = Path(__file__).parents[2] / "scripts" / "runtime" / "continuity" / "reap_stale_rdc_sessions.py"

def load_evidence():
    tree = ast.parse(MODULE.read_text(encoding="utf-8-sig"))
    keep = []
    wanted = {"TRANSPORT_DISCONNECT_MARKERS", "TRANSPORT_RECONNECT_MARKERS"}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in wanted for t in node.targets):
            keep.append(node)
        if isinstance(node, ast.FunctionDef) and node.name == "bounded_stdout_online_evidence":
            keep.append(node)
    ns = {"os": os}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(MODULE), "exec"), ns)
    return ns["bounded_stdout_online_evidence"]

def run_cases():
    fn = load_evidence()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    try:
        Path(path).write_bytes(b"Channel closed\nStatus: Online\n")
        assert fn(path)
        Path(path).write_bytes(b"Status: Online\nChannel closed\n")
        assert fn(path) is None
        Path(path).write_bytes(b"Status: Online\n" + b"x" * 70000)
        assert fn(path) is None
    finally:
        os.unlink(path)

if __name__ == "__main__":
    run_cases()
    print("RDC_BOUNDED_EVIDENCE_PASS")
