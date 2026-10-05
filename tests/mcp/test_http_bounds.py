import http.client
from pathlib import Path
import socket
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/ai-os'))
from raios_mcp import server
from raios_mcp.gateway import Gateway

def test_partial_body_times_out_while_health_remains_responsive(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'REQUEST_IO_TIMEOUT_SECONDS',.2,raising=False)
    handler=type('BoundedTestHandler',(server.Handler,),{'gateway':Gateway.from_root(tmp_path,grants=[])})
    httpd=server.ReuseHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    sock=socket.create_connection(httpd.server_address,timeout=2)
    try:
        sock.sendall(b'POST /mcp HTTP/1.1\r\nHost: localhost\r\nContent-Length: 100\r\n\r\n{')
        conn=http.client.HTTPConnection(*httpd.server_address,timeout=1)
        start=time.monotonic();conn.request('GET','/health');r=conn.getresponse()
        assert r.status==200;r.read();conn.close();assert time.monotonic()-start<1
        reply=sock.recv(4096)
        assert b'408' in reply
        assert b'REQUEST_TIMEOUT' in reply or b'Content-Length:' in reply
    finally:
        sock.close();httpd.shutdown();httpd.server_close();thread.join(timeout=2)

def test_oversized_body_is_rejected_without_draining(tmp_path):
    handler=type('BoundedTestHandler',(server.Handler,),{'gateway':Gateway.from_root(tmp_path,grants=[])})
    httpd=server.ReuseHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    sock=socket.create_connection(httpd.server_address,timeout=1)
    try:
        sock.sendall(f'POST /mcp HTTP/1.1\r\nHost: localhost\r\nContent-Length: {server.MAX_REQUEST_BYTES+1}\r\n\r\n'.encode())
        assert b'413' in sock.recv(4096)
    finally:
        sock.close();httpd.shutdown();httpd.server_close();thread.join(timeout=2)

def test_head_reads_git_worktree_and_ignores_environment(tmp_path,monkeypatch):
    metadata=tmp_path/'metadata';metadata.mkdir()
    common=tmp_path/'common';(common/'refs/heads').mkdir(parents=True)
    (metadata/'HEAD').write_text('ref: refs/heads/test\n')
    (metadata/'commondir').write_text('../common\n')
    (tmp_path/'.git').write_text('gitdir: metadata\n')
    sha='a'*40;(common/'refs/heads/test').write_text(sha+'\n')
    monkeypatch.setenv('RAIOS_CANONICAL_HEAD','b'*40)
    assert server.canonical_head(tmp_path)==(sha,'git-file')
