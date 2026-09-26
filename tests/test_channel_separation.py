import copy
import pytest
from src.autocad.channel_separation import verify

def fixture():
    channels={'A':[{'wire_handle':'A1','nodes':[['S','X1TERM01'],['M','X4TERM01']]}],
              'B':[{'wire_handle':'B1','nodes':[['S','X1TERM02'],['M','X4TERM02']]}]}
    rows={n['wire_handle']:{'success':True,'wire_handle':n['wire_handle'],'connections':copy.deepcopy(n['nodes'])} for nets in channels.values() for n in nets}
    return channels,rows

def test_same_device_distinct_terminals_allowed():
    c,r=fixture();d=verify(c,r)
    assert d['native_terminal_separation'] and not d['safety_function_validated']

def test_accidental_bridge_rejected():
    c,r=fixture();r['A1']['connections']+=r['B1']['connections']
    with pytest.raises(ValueError,match='unexpected'):verify(c,r)

def test_missing_terminal_rejected():
    c,r=fixture();r['B1']['connections'].pop()
    with pytest.raises(ValueError,match='Missing'):verify(c,r)

def test_shared_expected_terminal_rejected():
    c,r=fixture();c['B'][0]['nodes'][0]=c['A'][0]['nodes'][0];r['B1']['connections']=c['B'][0]['nodes']
    with pytest.raises(ValueError,match='share'):verify(c,r)

def test_shared_wire_rejected():
    c,r=fixture();c['B'][0]['wire_handle']='A1'
    with pytest.raises(ValueError,match='shared wire'):verify(c,r)
