import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/ai-os'))
from raios_mcp.gateway import Gateway,GatewayError,REGISTERED_TOOLS,V1_TOOLS

def write_policy(root,policy):
    directory=root/'.ai-os/mcp';directory.mkdir(parents=True,exist_ok=True)
    (directory/'POLICY.json').write_text(json.dumps(policy))

def test_configured_registry_mismatch_is_rejected(tmp_path):
    write_policy(tmp_path,{'v1_tools':list(V1_TOOLS),'execution_tools':[]})
    with pytest.raises(GatewayError) as e:Gateway.from_root(tmp_path)
    assert e.value.code=='CONFIGURATION_MISMATCH'

def test_canonical_seat_identity_preserves_policy_permissions(tmp_path):
    spec={'actor_role':'OLD','instance_role':'old','tools':list(REGISTERED_TOOLS),'deny':['execute_scoped_task']}
    write_policy(tmp_path,{'actors':{'C5':spec}})
    (tmp_path/'.ai-os/mcp/SEAT-MAP.json').write_text(json.dumps({
        'knowledge_state':'CANONICAL','seats':{'C5':{'actor_role':'RAIOS_LIVE_BRAIN','instance_role':'c5-runtime',
            'tools':['shell'],'deny':[]}}}))
    gw=Gateway.from_root(tmp_path,tokens={'C5':'test-token'})
    actor=gw.authenticate('test-token')
    assert actor.actor_role=='RAIOS_LIVE_BRAIN'
    assert actor.instance_role=='c5-runtime'
    assert actor.tools==list(REGISTERED_TOOLS)
    assert actor.deny==['execute_scoped_task']
    assert 'shell' not in actor.scopes
