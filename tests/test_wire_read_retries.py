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


@pytest.mark.parametrize('busy',[True,False])
def test_wrapped_read_only_query_busy(busy):
    from src.autocad.connection import AutoCADConnectionError
    error=AutoCADConnectionError('query failed')
    error.__cause__=RuntimeError(-2147418111 if busy else -2147024891,'fixture')
    with patch.object(electrical,'_inspect_wire_once',side_effect=[error,{'success':True}]) as probe,patch('src.autocad.com_runtime.time.sleep'):
        result=electrical.inspect_wire('A')
    assert result['success']==busy
    assert probe.call_count==(2 if busy else 1)


def test_busy_after_number_write_does_not_repeat_write():
    from src.autocad.connection import AutoCADConnectionError
    error=AutoCADConnectionError('query busy');error.__cause__=RuntimeError(-2147418111,'busy')
    doc=SimpleNamespace(HandleToObject=lambda h:SimpleNamespace(ObjectName='AcDbLine',Layer='TEST'))
    with patch.object(electrical,'connection',return_value=(object(),doc)),patch.object(electrical,'evaluate',side_effect=[['TEST'],True]) as call,patch.object(electrical,'_inspect_wire_once',side_effect=[error,{'success':True,'wire_number':'PWR0'}]),patch('src.autocad.com_runtime.time.sleep'):
        result=electrical.set_number('A','PWR0')
    assert result['success']
    assert sum('wd_putwn' in c.args[1] for c in call.call_args_list)==1
