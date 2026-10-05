"""Exercise the owned provider with a real stdio MCP child, never a hosted service."""
import json
import logging
import os
from pathlib import Path
import sys
import threading
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/ai-os'))
from raios_mcp.desktop_commander_provider import DesktopCommanderProvider, DesktopCommanderProviderError

CHILD = '''import json,sys,time,os
from pathlib import Path
root=Path(__file__).parent
(root/'pid').write_text(str(os.getpid()))
if (root/'stall_start').exists(): time.sleep(60)
for line in sys.stdin:
 m=json.loads(line); rid=m.get('id'); method=m['method']
 if rid is None: continue
 if method=='initialize':
  if (root/'malformed').exists():
   print('{"jsonrpc":"2.0","id":1,"result":"SECRET_INVALID_FRAME"}',flush=True);continue
  if (root/'large_frame').exists():
   sys.stdout.write('x'*131072);sys.stdout.flush();time.sleep(60)
  result={'protocolVersion':m['params']['protocolVersion'],'capabilities':{'tools':{}},'serverInfo':{'name':'fixture','version':'1'}}
 elif method=='tools/list':
  result={'tools':[{'name':'read_file','description':'fixture read','inputSchema':{'type':'object','required':['path'],'properties':{'path':{'type':'string'}},'additionalProperties':False}}]}
  if (root/'unsafe_schema').exists():result['tools'][0]['inputSchema']['properties']['path']['pattern']='^(a+)+$'
  if (root/'many_tools').exists():result={'tools':[{'name':str(i),'inputSchema':{'type':'object'}} for i in range(3)]}
 elif method=='tools/call':
  args=m['params']['arguments']; path=args['path']
  with (root/'calls').open('a') as f:f.write(path+'\\n')
  if path=='hang': time.sleep(60)
  if path=='fail': result={'isError':True,'content':[{'type':'text','text':'SECRET_DO_NOT_EXPOSE'}]}
  else:result={'content':[{'type':'text','text':'read:'+path}]}
 else:result={}
 print(json.dumps({'jsonrpc':'2.0','id':rid,'result':result}),flush=True)
'''

@pytest.fixture
def provider(tmp_path):
    entry=tmp_path/'provider.py'; entry.write_text(CHILD)
    p=DesktopCommanderProvider({'node':sys.executable,'entry':str(entry),
        'read_tools':['read_file'],'timeout_seconds':0.8,'admission_timeout_seconds':0.1})
    yield p,tmp_path
    p.close()

def test_denied_operation_does_not_start_provider(provider):
    p,root=provider
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('run_command',{'command':'anything'})
    assert e.value.code=='PROVIDER_TOOL_DENIED'
    assert not (root/'pid').exists()

def test_discovery_exports_function_schemas(provider):
    p,_=provider
    status=p.call('__list_tools__')
    assert status['sdk']=='mcp'
    assert status['tools'][0]['inputSchema']['required']==['path']
    assert status['functions'][0]['type']=='function'
    assert status['functions'][0]['function']['parameters']['required']==['path']

def test_real_sdk_execution_and_argument_validation(provider):
    p,root=provider
    r=p.call('read_file',{'path':'ok'})
    assert r['result']['content'][0]['text']=='read:ok'
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('read_file',{'path':42})
    assert e.value.code=='INVALID_ARGUMENTS'
    assert (root/'calls').read_text()=='ok\n'

@pytest.mark.parametrize('startup',[False,True])
def test_hung_child_has_bounded_timeout_and_next_call_recovers(provider,startup):
    p,root=provider
    if startup:(root/'stall_start').touch()
    start=time.monotonic()
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('read_file',{'path':'hang'})
    assert e.value.code=='MCP_PROVIDER_TIMEOUT'
    assert time.monotonic()-start<5
    pid=int((root/'pid').read_text())
    if os.name!='nt':
        with pytest.raises(ProcessLookupError):os.kill(pid,0)
    (root/'stall_start').unlink(missing_ok=True)
    assert p.call('read_file',{'path':'after'})['result']['content'][0]['text']=='read:after'

def test_busy_provider_and_status_never_wait_for_running_tool(provider):
    p,root=provider; failures=[]
    def run():
        try:p.call('read_file',{'path':'hang'})
        except DesktopCommanderProviderError as e:failures.append(e.code)
    t=threading.Thread(target=run);t.start()
    try:
        deadline=time.monotonic()+2
        while not (root/'calls').exists() and time.monotonic()<deadline:time.sleep(.01)
        assert (root/'calls').exists()
        start=time.monotonic();assert p.status()['busy'] is True
        with pytest.raises(DesktopCommanderProviderError) as e:p.call('read_file',{'path':'other'})
        assert e.value.code=='PROVIDER_BUSY'
        assert time.monotonic()-start<.5
    finally:t.join(timeout=5)
    assert failures==['MCP_PROVIDER_TIMEOUT']

def test_provider_error_does_not_expose_contents(provider):
    p,_=provider
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('read_file',{'path':'fail'})
    assert e.value.code=='PROVIDER_TOOL_ERROR'
    assert 'SECRET_DO_NOT_EXPOSE' not in str(e.value)

@pytest.mark.parametrize('value',[0,-1,float('inf'),float('nan')])
def test_invalid_timeout_rejected(value):
    with pytest.raises(DesktopCommanderProviderError) as e:DesktopCommanderProvider({'timeout_seconds':value})
    assert e.value.code=='INVALID_PROVIDER_CONFIG'

def test_invalid_frame_never_logs_provider_contents(provider,caplog):
    p,root=provider;(root/'malformed').touch()
    with caplog.at_level(logging.ERROR), pytest.raises(DesktopCommanderProviderError):p.call('read_file',{'path':'ok'})
    assert 'SECRET_INVALID_FRAME' not in caplog.text

def test_unterminated_frame_is_bounded_before_sdk_parse(provider):
    p,root=provider;p.max_frame_bytes=65536;(root/'large_frame').touch()
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('read_file',{'path':'ok'})
    assert e.value.code=='PROVIDER_FRAME_TOO_LARGE'

def test_disallowed_discovery_tools_count_towards_limit(provider):
    p,root=provider;p.max_tools=1;(root/'many_tools').touch()
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('__list_tools__')
    assert e.value.code=='MCP_TOOLS_INVALID'

def test_discovery_schema_bytes_are_bounded(provider):
    p,_=provider;p.max_discovery_bytes=10
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('__list_tools__')
    assert e.value.code=='MCP_TOOLS_INVALID'

def test_expensive_schema_validation_cannot_block_gateway(provider):
    p,root=provider;p.timeout_seconds=.4;(root/'unsafe_schema').touch()
    start=time.monotonic()
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('read_file',{'path':'a'*26+'!'})
    assert e.value.code=='MCP_PROVIDER_TIMEOUT'
    assert time.monotonic()-start<1.5

def test_stalled_stdin_is_covered_by_provider_deadline(provider):
    p,root=provider;(root/'stall_start').touch()
    start=time.monotonic()
    with pytest.raises(DesktopCommanderProviderError) as e:p.call('read_file',{'path':'a'*500000})
    assert e.value.code=='MCP_PROVIDER_TIMEOUT'
    assert time.monotonic()-start<5

def test_function_call_runs_through_authenticated_http_gateway(provider,tmp_path):
    import anyio
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from raios_mcp.gateway import Gateway
    from raios_mcp.server import Handler,ReuseHTTPServer
    p,_=provider
    policy={'actors':{'C5':{'actor_role':'RAIOS','instance_role':'test',
        'tools':['execute_scoped_task'],'deny':[]}},
        'providers':{'desktop_commander':{'enabled':True}}}
    (tmp_path/'.ai-os/mcp').mkdir(parents=True)
    (tmp_path/'.ai-os/mcp/POLICY.json').write_text(json.dumps(policy))
    gw=Gateway.from_root(tmp_path,tokens={'C5':'fixture-only-token'})
    gw._remote_provider=p
    handler=type('ExecutionHandler',(Handler,),{'gateway':gw})
    httpd=ReuseHTTPServer(('127.0.0.1',0),handler)
    t=threading.Thread(target=httpd.serve_forever,daemon=True);t.start()
    async def run():
        url=f'http://127.0.0.1:{httpd.server_address[1]}/mcp'
        import httpx
        async with httpx.AsyncClient(headers={'Authorization':'Bearer fixture-only-token'}) as http_client, streamable_http_client(url,http_client=http_client) as (r,w,_):
            async with ClientSession(r,w) as client:
                await client.initialize()
                tools=await client.list_tools();assert 'execute_scoped_task' in [x.name for x in tools.tools]
                result=await client.call_tool('execute_scoped_task',{
                    'provider':'desktop_commander','capability':'remote','operation':'read_file',
                    'arguments':{'path':'from-function-call'},'mode':'READ_ONLY',
                    'execution_intent':'SCOPED','authority_scope':'REMOTE_CAPABILITY_READ'})
                assert result.isError is False
                data=json.loads(result.content[0].text)
                assert data['result']['result']['content'][0]['text']=='read:from-function-call'
                denied=await client.call_tool('execute_scoped_task',{
                    'provider':'desktop_commander','capability':'remote','operation':'read_file',
                    'arguments':{'path':'never-executed'},'mode':'WRITE',
                    'execution_intent':'SCOPED','authority_scope':'REMOTE_CAPABILITY_READ'})
                assert denied.isError is True
                assert json.loads(denied.content[0].text)['error']=='MUTATION_NOT_ENABLED'
    try:anyio.run(run)
    finally:httpd.shutdown();httpd.server_close();t.join(timeout=2);gw.close()
