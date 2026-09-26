"""Synthetic adapter failures, not live CAD crash tests."""
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.tools import trebi_batch as batch

@pytest.mark.parametrize('failure',['insert_exception','insert_return','wire','number','backup_failed'])
def test_partial_batch_keeps_evidence_and_never_continues(tmp_path,failure):
    spec=json.loads((batch.ROOT/'examples/trebi-batch.json').read_text(encoding='utf8'))
    project=tmp_path/'test.wdp';project.write_text('*[20]2',encoding='utf8')
    project.with_suffix('.wdt').write_text(batch.WDT.read_text(encoding='utf8'),encoding='utf8')
    for name,_ in batch.SYMBOLS.values():(tmp_path/(name+'.dwg')).touch()
    docs=[]
    for entry in spec['manifest']['entries']:
        doc=MagicMock();doc.FullName=str(tmp_path/entry['drawing_file']);doc.Saved=True
        doc.ModelSpace=[MagicMock(ObjectName='AcDbBlockReference',Name=name) for name in ['WD_M',batch.profile()['block_name']]]
        docs.append(doc)
    conn=MagicMock();app=conn.get_application.return_value;app.HWND=7;app.Documents=docs;app.ActiveDocument=docs[-1]
    conn.get_active_document.side_effect=lambda:app.ActiveDocument
    for doc in docs:doc.Activate.side_effect=lambda d=doc:setattr(app,'ActiveDocument',d)
    state={'project':str(project),'drawings':[d.FullName for d in docs]}
    inserted=[]
    def insert(*args,**kwargs):
        handle=format(160+len(inserted),'X');inserted.append(handle)
        if len(inserted)==2:
            if failure=='insert_exception':raise RuntimeError('COM failed after possible insertion')
            if failure=='insert_return':return {'success':False,'created_handle':handle,'error':'attribute readback failed'}
        return {'success':True,'handle':handle,'attributes':kwargs['attributes']}
    with ExitStack() as stack:
        stack.enter_context(patch('src.autocad.engineering_archive.backup_saved_project',side_effect=OSError('backup unavailable') if failure=='backup_failed' else None,return_value={'files':[],'path':'fixture'}))
        def mocked(target,**kwargs):return stack.enter_context(patch(target,**kwargs))
        stack.enter_context(patch.object(batch,'ROOT',tmp_path));stack.enter_context(patch.object(batch,'LIB',tmp_path))
        mocked('src.autocad.connection.get_connection',return_value=conn)
        mocked('src.tools.native_project.guard',return_value=state)
        mocked('src.autocad.utils.get_block_attributes',side_effect=lambda obj:batch.settings('54') if obj.Name=='WD_M' else {'PAGE':'54','OF':'2','PREV':'-','NEXT':'112'})
        mocked('src.autocad.com_runtime.wait_for_document',side_effect=lambda a,p:a.ActiveDocument)
        mocked('src.autocad.lisp_bridge.evaluate',return_value=True)
        stack.enter_context(patch.object(batch,'configure',return_value={'success':True}))
        stack.enter_context(patch.object(batch,'apply_title',return_value={'success':True}))
        ins=mocked('src.tools.native_electrical.insert_symbol',side_effect=insert)
        wire=mocked('src.tools.native_electrical.connect_terminals',return_value={'success':True,'wire_handles':['F01']})
        if failure=='wire':wire.side_effect=RuntimeError('wire submission outcome unknown')
        number=mocked('src.tools.native_electrical.set_number',side_effect=RuntimeError('number submission outcome unknown'))
        export=mocked('src.tools.native_project.export_report')
        result=batch.execute(str(project),spec,docs[-1].FullName)
    if failure=='backup_failed':
        assert not result['success'] and result['submitted'] is False
        ins.assert_not_called();wire.assert_not_called();number.assert_not_called();export.assert_not_called()
        for doc in docs:doc.Activate.assert_not_called();doc.Save.assert_not_called()
        return
    assert not result['success'] and result['submitted'] is True
    assert result['status']=='partial_or_unknown' and result['automatic_retry'] is False
    journal=json.loads(Path(result['receipt']).read_text(encoding='utf8'))
    assert journal==result
    assert journal['failed_step']==journal['steps'][-1]['step']
    assert all(s['status']=='completed' for s in journal['steps'][:-1])
    export.assert_not_called()
    if failure.startswith('insert'):
        assert ins.call_count==2 and len(journal['entities'])==1
        wire.assert_not_called();number.assert_not_called()
        assert next(iter(journal['entities'].values()))['handle']==inserted[0]
        if failure=='insert_return':
            assert journal['steps'][-1]['result']['created_handle']==inserted[1]
            assert journal['steps'][-1]['status']=='failed'
        else:assert journal['steps'][-1]['status']=='failed_or_unknown'
    else:
        assert ins.call_count==len(spec['components'])
        expected_wire_calls=1 if failure=='wire' else next(i+1 for i,w in enumerate(spec['connections']) if w.get('wire_number'))
        assert wire.call_count==expected_wire_calls
        if failure=='wire':
            number.assert_not_called();assert not journal['wires']
        else:
            number.assert_called_once();assert len(journal['wires'])==expected_wire_calls
            assert next(iter(journal['wires'].values()))['wire_handles']==['F01']
