import pytest
from unittest.mock import patch
from src.tools.trebi_test_changes import validate,execute

@pytest.fixture
def spec():return {'purpose':'test_only','action':'lamp_green_to_red','drawing_sha256':'a'*64,'component_handle':'A7B','peer_handle':'C01','wire_handles':['A01','A02']}

@pytest.mark.parametrize('case',['production','unknown_action','hash','handle','extra','wire_count','duplicate_wire','wrong_type'])
def test_reject_before_cad(spec,case):
    if case=='production':spec['purpose']='production'
    if case=='unknown_action':spec['action']='arbitrary_delete'
    if case=='hash':spec['drawing_sha256']='unknown'
    if case=='handle':spec['component_handle']='(command)'
    if case=='extra':spec['new_catalog']='arbitrary'
    if case=='wire_count':spec['wire_handles']=[]
    if case=='duplicate_wire':spec['wire_handles']=['A01','A01']
    if case=='wrong_type':spec['peer_handle']=None
    with patch('src.autocad.connection.get_connection') as conn:
        result=execute('C:/test.wdp','C:/test.dwg',spec)
    assert not result['success'] and not result['submitted']
    conn.assert_not_called()

def test_saved_hash_mismatch_never_contacts_cad(tmp_path,spec):
    file=tmp_path/'saved.dwg';file.write_bytes(b'changed')
    with patch('src.autocad.connection.get_connection') as conn:
        result=execute(str(tmp_path/'test.wdp'),str(file),spec)
    assert not result['submitted'];conn.assert_not_called()

def test_exact_two_actions(spec):
    assert validate(spec) is spec
    spec['action']='output_y00_to_y01';spec['wire_handles']=['A01']
    assert validate(spec) is spec

@pytest.mark.parametrize('submitted',[False,True])
def test_change_preflight_does_not_release_unknown_write(tmp_path,submitted):
    from src.autocad.isolated import isolated,diagnose
    def execute_trebi_test_change():pass
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'), patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'), patch('src.autocad.isolated.run_worker',return_value={'success':False,'status':'preflight_rejected','submitted':submitted}):
        result=isolated(execute_trebi_test_change)()
        assert (diagnose()['marker'] is None)==(not submitted)
        assert result['status']==('outcome_unknown' if submitted else 'preflight_rejected')

@pytest.mark.parametrize('failure',['swap_exception','color_rejected','backup_failed'])
def test_partial_change_stops_without_saving(tmp_path,failure):
    import json,hashlib
    from contextlib import ExitStack
    from unittest.mock import MagicMock
    from src.tools import trebi_test_changes as changes
    drawing=tmp_path/'test.dwg';drawing.write_bytes(b'original')
    asset=tmp_path/'HLT1R.dwg';asset.write_bytes(b'fixture')
    args={'purpose':'test_only','action':'lamp_green_to_red','drawing_sha256':hashlib.sha256(drawing.read_bytes()).hexdigest(),
          'component_handle':'AA','peer_handle':'BB','wire_handles':['C1','C2']}
    attrs={'TAG1':'-405H1','MFG':'KINTO_TEST','CAT':'LAMP_24V_TEST','COLOR':'GN','TERM01':'1','TERM02':'2'}
    conn=MagicMock();doc=conn.get_active_document.return_value;doc.FullName=str(drawing);doc.Saved=True
    obj=doc.HandleToObject.return_value;obj.Handle='AA';obj.Name='HLT1G'
    wires=[{'success':True,'wire_number':n,'connections':[['AA',tag],['BB','X1TERM01']]} for n,tag in [('TEST_DO','X4TERM01'),('TEST0','X1TERM02')]]
    with ExitStack() as stack:
        stack.enter_context(patch.object(changes,'backup_saved_project',side_effect=OSError('backup failed') if failure=='backup_failed' else None,return_value={'path':'test-backup'}))
        stack.enter_context(patch.object(changes,'ROOT',tmp_path));stack.enter_context(patch.object(changes,'LAMP_SYMBOL',asset))
        stack.enter_context(patch('src.autocad.connection.get_connection',return_value=conn))
        stack.enter_context(patch('src.autocad.utils.get_block_attributes',return_value=attrs))
        stack.enter_context(patch('src.autocad.change_audit.snapshot',return_value={}))
        stack.enter_context(patch('src.tools.native_project.guard',return_value={'project':'fixture'}))
        stack.enter_context(patch('src.tools.native_electrical.inspect_wire',side_effect=wires))
        evaluate=stack.enter_context(patch('src.autocad.lisp_bridge.evaluate',side_effect=RuntimeError('outcome uncertain') if failure=='swap_exception' else [['DD',None],0]))
        connect=stack.enter_context(patch('src.tools.native_electrical.connect_terminals'))
        result=changes.execute(str(tmp_path/'test.wdp'),str(drawing),args)
    if failure=='backup_failed':
        assert result['status']=='preflight_rejected' and result['submitted'] is False
        evaluate.assert_not_called();doc.Save.assert_not_called();connect.assert_not_called()
        return
    assert result['status']=='partial_or_unknown' and result['submitted'] and not result['automatic_retry']
    assert evaluate.call_count==(1 if failure=='swap_exception' else 2)
    doc.Save.assert_not_called();connect.assert_not_called()
    journal=json.loads(__import__('pathlib').Path(result['receipt']).read_text())
    assert journal['steps'][-1]['status']=='failed_or_unknown'
    assert journal['failed_step']==('native_swap' if failure=='swap_exception' else 'color')
    if failure=='color_rejected':assert journal['new_handle']=='DD'


@pytest.mark.parametrize('failure', [None, 'number', 'layer', 'extra_endpoint', 'old_channel', 'read_failed'])
def test_numbered_route_requires_each_segment_readback(failure):
    from copy import deepcopy
    from src.tools.trebi_test_changes import verify_reconnected_wires
    row = {'success': True, 'wire_number': 'TEST_DO', 'wire_layer': 'TEST_SIGNAL',
           'connections': [['aa', 'X1TERM34'], ['bb', 'X4TERM01']]}
    rows = [deepcopy(row) for _ in range(3)]
    if failure == 'number': rows[2]['wire_number'] = 'OTHER'
    if failure == 'layer': rows[2]['wire_layer'] = '0'
    if failure == 'extra_endpoint': rows[2]['connections'].append(['CC', 'X1TERM01'])
    if failure == 'old_channel': rows[2]['connections'][0][1] = 'X1TERM33'
    if failure == 'read_failed': rows[2]['success'] = False
    with patch('src.tools.native_electrical.inspect_wire', side_effect=rows) as read:
        if failure:
            with pytest.raises(RuntimeError, match='readback mismatch'):
                verify_reconnected_wires(['D1', 'D2', 'D3'], 'AA', 'BB')
        else:
            assert verify_reconnected_wires(['D1', 'D2', 'D3'], 'AA', 'BB')['success']
        assert [c.args[0] for c in read.call_args_list] == ['D1', 'D2', 'D3']


@pytest.mark.parametrize('handles', [['D1', 'd1', 'D3'], ['D1', 'D2']])
def test_invalid_route_does_not_read_cad(handles):
    from src.tools.trebi_test_changes import verify_reconnected_wires
    with patch('src.tools.native_electrical.inspect_wire') as read:
        with pytest.raises(RuntimeError, match='distinct'):
            verify_reconnected_wires(handles, 'AA', 'BB')
        read.assert_not_called()


def test_saved_project_backup_inventory(tmp_path):
    from src.tools.trebi_test_changes import backup_saved_project
    from src.autocad.engineering_archive import verify
    source=tmp_path/'source';source.mkdir()
    for name in ['test.wdp','test.wdt','page.dwg']:
        (source/name).write_bytes(name.encode())
    result=backup_saved_project(source/'test.wdp',{'drawings':[str(source/'page.dwg')]},tmp_path/'archive')
    assert len(verify(result['path'])['files'])==3
    assert not result['external_dependencies_included']


def test_saved_project_backup_rejects_external_drawing(tmp_path):
    from src.tools.trebi_test_changes import backup_saved_project
    with pytest.raises(ValueError,match='one directory'):
        backup_saved_project(tmp_path/'source/test.wdp',{'drawings':[str(tmp_path/'other.dwg')]},tmp_path/'archive')
    assert not (tmp_path/'archive').exists()
