from types import SimpleNamespace
from unittest.mock import patch
import pytest
from src.tools import native_electrical as electrical

@pytest.mark.parametrize('fault',['point_lookup','wire_read','write_failure'])
def test_busy_reads_never_repeat_wire_insertion(fault):
    class Wire:
        Layer='TEST';reads=0
        @property
        def ObjectName(self):
            self.reads+=1
            if fault=='wire_read' and self.reads==1:raise RuntimeError(-2147418111,'busy')
            return 'AcDbLine'
    wire=Wire()
    class Doc:
        ModelSpace=[];lookups=0
        def HandleToObject(self,h):
            if h=='A':
                self.lookups+=1
                if fault=='point_lookup' and self.lookups==1:raise RuntimeError(-2147418111,'busy')
            return wire if h=='C' else SimpleNamespace(handle=h)
    calls=[]
    def evaluate(conn,expression):
        calls.append(expression)
        if 'ace_get_wiretype_list' in expression:return ['TEST']
        assert 'ace_insert_wire' in expression
        if fault=='write_failure':raise RuntimeError('write outcome unknown')
        return ['C']
    def points(obj):return [{'connection':'X1TERM01' if obj.handle=='A' else 'X4TERM01','position':[0,0,0] if obj.handle=='A' else [10,0,0]}]
    with patch.object(electrical,'connection',return_value=(object(),Doc())),patch.object(electrical,'evaluate',side_effect=evaluate),patch.object(electrical,'_points',side_effect=points),patch.object(electrical,'network',return_value=[['A','X1TERM01'],['B','X4TERM01']]),patch('src.autocad.com_runtime.time.sleep'):
        result=electrical.connect_terminals('A','X1TERM01','B','X4TERM01','TEST')
    assert sum('ace_insert_wire' in x for x in calls)==1
    if fault=='write_failure':
        assert not result['success'] and result['write_attempted'] and result['phase']=='insert_wire'
    else:assert result['success']
