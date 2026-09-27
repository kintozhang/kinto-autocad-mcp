import json
from pathlib import Path
from unittest.mock import patch
import pytest
from src.autocad import recovery
from src.autocad.isolated import isolated,diagnose

@pytest.fixture
def scene(tmp_path):
    lock=tmp_path/'session.lock';op='a'*32
    lock.write_bytes(b'\0'+json.dumps({'pid':999,'operation':'draw_line:'+op}).encode())
    ops=tmp_path/'operations';ops.mkdir()
    (ops/(op+'.json')).write_text(json.dumps({'state':'outcome_unknown','tool':'draw_line'}))
    (ops/(op+'.progress')).write_text(json.dumps({'pid':998,'state':'tool_entering'}))
    drawing=tmp_path/'draft.dwg';drawing.write_bytes(b'draft')
    with patch.object(recovery,'gate_path',return_value=lock),patch.object(recovery,'probe_worker',return_value={'idle':True,'saved':True,'objects':[]}) as probe,patch('win32process.EnumProcesses',return_value=[]) as processes:
        yield lock,op,str(drawing),probe,processes

def test_inspection_preserves_marker_release_preserves_unknown(scene):
    lock,op,drawing,probe,_=scene;before=lock.read_bytes()
    d=recovery.inspect_or_release('inspect',drawing,123)
    assert d['status']=='review_required' and lock.read_bytes()==before
    r=recovery.inspect_or_release('release',drawing,123,op,d['snapshot_id'])
    assert r['failed_operation_status']=='partial_or_unknown' and not r['cad_modified']
    assert lock.read_bytes()==b'\0' and Path(r['receipt']).exists()

def test_live_worker_cannot_be_released(scene):
    lock,op,drawing,probe,processes=scene;processes.return_value=[998]
    with pytest.raises(ValueError,match='alive'):recovery.inspect_or_release('inspect',drawing,123)
    probe.assert_not_called();assert len(lock.read_bytes())>1

def test_changed_objects_refuse_release(scene):
    lock,op,drawing,probe,_=scene
    d=recovery.inspect_or_release('inspect',drawing,123)
    probe.return_value={'idle':True,'saved':True,'objects':[{'handle':'new'}]}
    with pytest.raises(ValueError,match='changed'):recovery.inspect_or_release('release',drawing,123,op,d['snapshot_id'])
    assert len(lock.read_bytes())>1

def test_changed_record_refuses_release(scene):
    lock,op,drawing,probe,_=scene;d=recovery.inspect_or_release('inspect',drawing,123)
    (lock.parent/'operations'/(op+'.json')).write_text(json.dumps({'state':'outcome_unknown','changed':True}))
    with pytest.raises(ValueError,match='changed'):recovery.inspect_or_release('release',drawing,123,op,d['snapshot_id'])

def test_wrong_operation_and_path_token_refused(scene):
    lock,op,drawing,probe,_=scene
    with pytest.raises(ValueError,match='Exact'):recovery.inspect_or_release('release',drawing,123,'b'*32,'../bad')
    assert len(lock.read_bytes())>1

def test_read_failure_keeps_marker(scene):
    lock,op,drawing,probe,_=scene;probe.side_effect=TimeoutError('busy')
    with pytest.raises(TimeoutError):recovery.inspect_or_release('inspect',drawing,123)
    assert len(lock.read_bytes())>1

def test_invalid_action_never_reads_cad(scene):
    lock,op,drawing,probe,_=scene
    with pytest.raises(ValueError):recovery.inspect_or_release('retry',drawing,123)
    probe.assert_not_called()

def test_active_gate_refuses_probe(scene):
    import msvcrt
    lock,op,drawing,probe,_=scene
    with lock.open('r+b',buffering=0) as f:
        msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        try:assert recovery.inspect_or_release('inspect',drawing,123)['status']=='cad_in_use'
        finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
    probe.assert_not_called()

@pytest.mark.parametrize("name", ["export_electrical_project_pdf", "insert_test_parametric_connector", "insert_test_plc_module"])
def test_preflight_does_not_quarantine(tmp_path, name):
    def export_electrical_project_pdf():pass
    export_electrical_project_pdf.__name__=name
    result={'success':False,'status':'preflight_rejected','submitted':False,'operation_directory':None}
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'),patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'),patch('src.autocad.isolated.run_worker',return_value=result):
        assert isolated(export_electrical_project_pdf)()==result
        assert diagnose()['marker'] is None

def test_pdf_postwrite_failure_still_quarantines(tmp_path):
    def export_electrical_project_pdf():pass
    result={'success':False,'status':'partial_or_unknown','submitted':True}
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'),patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'),patch('src.autocad.isolated.run_worker',return_value=result):
        assert isolated(export_electrical_project_pdf)()['status']=='outcome_unknown'
        assert diagnose()['marker']


def test_mtext_reference_snapshot_detects_content_and_geometry_changes():
    from types import SimpleNamespace
    from src.autocad.recovery_probe import entity_snapshot
    obj=SimpleNamespace(Handle='AB',ObjectName='AcDbMText',Layer='XREF',TextString='102.2,102.2',InsertionPoint=(1,2,0),Height=2.,Width=30.,Rotation=0.,AttachmentPoint=1,DrawingDirection=1,StyleName='STANDARD')
    first=entity_snapshot(obj);obj.TextString='102.9'
    assert recovery.fingerprint(first)!=recovery.fingerprint(entity_snapshot(obj))
    obj.TextString=first['text'];obj.Width=31.
    assert recovery.fingerprint(first)!=recovery.fingerprint(entity_snapshot(obj))
    obj.ObjectName='AcDbHatch'
    with pytest.raises(ValueError,match='unsupported'):entity_snapshot(obj)

@pytest.mark.parametrize('property,value',[('Radius',2.),('StartAngle',0.1),('EndAngle',2.),('Normal',(0,1,0)),('Thickness',1.)])
def test_arc_recovery_tracks_geometry(property,value):
    from types import SimpleNamespace
    from src.autocad.recovery_probe import entity_snapshot
    obj=SimpleNamespace(Handle='A',ObjectName='AcDbArc',Layer='WIRE',Center=(1,2,0),Radius=1.,StartAngle=0.,EndAngle=3.14,Normal=(0,0,1),Thickness=0.)
    before=recovery.fingerprint(entity_snapshot(obj));setattr(obj,property,value)
    assert recovery.fingerprint(entity_snapshot(obj))!=before

@pytest.mark.parametrize('change',['coordinate','bulge','width','closed','elevation'])
def test_polyline_recovery_tracks_each_segment(change):
    from types import SimpleNamespace
    from src.autocad.recovery_probe import entity_snapshot
    bulges=[0.,0.];widths=[(0.,0.),(0.,0.)]
    obj=SimpleNamespace(Handle='P',ObjectName='AcDbPolyline',Layer='WIRE',Coordinates=[0,0,1,1],Elevation=0.,Closed=False,Normal=(0,0,1),Thickness=0.,GetBulge=lambda i:bulges[i],GetWidth=lambda i:widths[i])
    before=recovery.fingerprint(entity_snapshot(obj))
    if change=='coordinate':obj.Coordinates[-1]=2
    if change=='bulge':bulges[0]=0.5
    if change=='width':widths[0]=(1.,2.)
    if change=='closed':obj.Closed=True
    if change=='elevation':obj.Elevation=1.
    assert recovery.fingerprint(entity_snapshot(obj))!=before

@pytest.mark.parametrize('submitted',[False,True,'unknown'])
def test_planning_only_batch_rejection_does_not_quarantine_unless_submitted(tmp_path,submitted):
    def execute_trebi_batch():pass
    result={'success':False,'status':'qualification_required','submitted':submitted}
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'),patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'),patch('src.autocad.isolated.run_worker',return_value=result):
        reply=isolated(execute_trebi_batch)()
        if submitted is False:
            assert reply==result and diagnose()['marker'] is None
        else:
            assert reply['status']=='outcome_unknown' and diagnose()['marker']
