import copy
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from src.tools.trebi_batch import plan, execute
from src.autocad.isolated import isolated, diagnose

@pytest.fixture
def spec():
    return json.loads((Path(__file__).resolve().parents[1]/'examples/trebi-batch.json').read_text(encoding='utf8'))

def test_logical_address_and_inherited_identity(spec):
    data=plan(spec)
    assert data['pages']['effective_drawing_count']==2
    assert [c['tag'] for c in data['component_plan']['components']]==['-112K1','-112K1']
    assert {r['value'] for r in data['expected_references']}=={'112.8','54.2','54.5'}
    assert data['submitted'] is False

@pytest.mark.parametrize('case',['wrong_parent','out_of_frame','tag_override','missing_signal','mismatched_number','cross_page_wire','bad_pin','duplicate_terminal','duplicate_wire','unknown_field','diagonal','filename_alias','backwards_pin'])
def test_invalid_entire_batch_never_contacts_cad(spec,case):
    if case=='wrong_parent':spec['components'][1]['parent_id']='terminal54'
    if case=='out_of_frame':spec['components'][0]['x']=float('nan')
    if case=='tag_override':spec['components'][0]['attributes']['TAG1']='K1'
    if case=='missing_signal':spec['components'].pop()
    if case=='mismatched_number':spec['connections'][0]['wire_number']='999'
    if case=='cross_page_wire':spec['connections'][0]['to_id']='terminal54'
    if case=='bad_pin':spec['connections'][0]['to_connection']='TERMDESC1'
    if case=='duplicate_terminal':spec['components'][4].update(strip='X112')
    if case=='duplicate_wire':spec['connections'].append({**spec['connections'][0],'id':'extra'})
    if case=='unknown_field':spec['components'][0]['code']='arbitrary lisp'
    if case=='diagonal':spec['components'][3]['y']=211
    if case=='filename_alias':spec['manifest']['entries'][1]['drawing_file']='DEMO-54.DWG'
    if case=='backwards_pin':spec['connections'][0]['to_connection']='X1TERM01'
    with patch('src.autocad.connection.get_connection') as conn:
        result=execute('C:/test/test.wdp',spec,'C:/test/demo-54.dwg')
    assert not result['success'] and result['submitted'] is False
    conn.assert_not_called()

@pytest.mark.parametrize('submitted',[False,True])
def test_only_proven_batch_preflight_releases_gate(tmp_path,submitted):
    def execute_trebi_batch():pass
    with patch('src.autocad.isolated.gate_path',return_value=tmp_path/'session.lock'), patch('src.autocad.client_gate.gate_path',return_value=tmp_path/'session.lock'), patch('src.autocad.isolated.run_worker',return_value={'success':False,'status':'preflight_rejected','submitted':submitted}):
        result=isolated(execute_trebi_batch)()
        assert (diagnose()['marker'] is None)==(not submitted)
        assert result['status']==('outcome_unknown' if submitted else 'preflight_rejected')

@pytest.mark.parametrize('populated',[True,False])
def test_all_pages_preflight_before_write_and_stop_on_first_failure(spec,tmp_path,populated):
    from contextlib import ExitStack
    from unittest.mock import MagicMock
    from src.tools import trebi_batch as batch
    project=tmp_path/'test.wdp';project.write_text('*[20]2',encoding='utf8')
    project.with_suffix('.wdt').write_text(batch.WDT.read_text(encoding='utf8'),encoding='utf8')
    for name,_ in batch.SYMBOLS.values():(tmp_path/(name+'.dwg')).touch()
    docs=[]
    for entry in spec['manifest']['entries']:
        doc=MagicMock();doc.FullName=str(tmp_path/entry['drawing_file']);doc.Saved=True
        objects=[]
        for name in ['WD_M',batch.profile()['block_name']]:
            obj=MagicMock();obj.ObjectName='AcDbBlockReference';obj.Name=name
            objects.append(obj)
        doc.ModelSpace=objects;docs.append(doc)
    if populated:
        docs[-1].ModelSpace.append(MagicMock(ObjectName='AcDbLine'))
        docs[-1].Saved=False  # Populated-drawing rejection must precede unsaved-state rejection.
    conn=MagicMock();app=conn.get_application.return_value;app.HWND=7;app.Documents=docs;app.ActiveDocument=docs[-1]
    conn.get_active_document.side_effect=lambda:app.ActiveDocument
    for doc in docs:doc.Activate.side_effect=lambda d=doc:setattr(app,'ActiveDocument',d)
    state={'project':str(project),'drawings':[d.FullName for d in docs]}
    with ExitStack() as stack:
        stack.enter_context(patch.object(batch,'LIB',tmp_path));stack.enter_context(patch.object(batch,'ROOT',tmp_path))
        stack.enter_context(patch('src.autocad.connection.get_connection',return_value=conn))
        stack.enter_context(patch('src.tools.native_project.guard',return_value=state))
        stack.enter_context(patch('src.autocad.utils.get_block_attributes',side_effect=lambda obj:batch.settings('54') if obj.Name=='WD_M' else {'PAGE':'54','OF':'2','PREV':'-','NEXT':'112'}))
        stack.enter_context(patch('src.autocad.com_runtime.wait_for_document',side_effect=lambda a,p:a.ActiveDocument))
        stack.enter_context(patch('src.autocad.lisp_bridge.evaluate',return_value=True))
        stack.enter_context(patch('src.autocad.engineering_archive.backup_saved_project',return_value={'files':[],'path':'fixture'}))
        configure=stack.enter_context(patch.object(batch,'configure',side_effect=RuntimeError('write outcome unknown')))
        insert=stack.enter_context(patch('src.tools.native_electrical.insert_symbol'))
        result=batch.execute(str(project),spec,docs[-1].FullName)
    insert.assert_not_called()
    if populated:
        configure.assert_not_called()
        assert 'populated drawings' in result['error']
        for doc in docs:doc.Activate.assert_not_called()
        assert result['status']=='preflight_rejected' and result['submitted'] is False
    else:
        configure.assert_called_once()
        assert result['status']=='partial_or_unknown' and result['automatic_retry'] is False
        journal=json.loads(Path(result['receipt']).read_text(encoding='utf8'))
        assert journal['steps'][-1]['step']=='grid:54'
        assert journal['steps'][-1]['status']=='failed_or_unknown'
        assert journal['failed_step']=='grid:54'
        assert journal['steps'][-1]['automatic_retry'] is False
        assert 'write outcome unknown' in journal['steps'][-1]['error']

@pytest.mark.parametrize('defect',['wrong_pin','wrong_handle','missing_endpoint','wrong_layer','wrong_number','failure'])
def test_final_wire_checks_catch_identity_changes_even_with_matching_number(defect):
    from src.tools.trebi_batch import verify_wire_readback
    link={'id':'w','from_id':'a','to_id':'b','from_connection':'X1TERM01','to_connection':'X4TERM01','wire_layer':'TEST_SIGNAL'}
    entities={'a':{'handle':'AB'},'b':{'handle':'CD'}}
    result={'success':True,'connections':[['ab','X1TERM01'],['cd','X4TERM01']],'wire_layer':'TEST_SIGNAL','wire_number':'101'}
    assert verify_wire_readback(link,entities,result,'101')['success']
    if defect=='wrong_pin':result['connections'][1][1]='X4TERM02'
    if defect=='wrong_handle':result['connections'][1][0]='EF'
    if defect=='missing_endpoint':result['connections'].pop()
    if defect=='wrong_layer':result['wire_layer']='OTHER_POTENTIAL'
    if defect=='wrong_number':result['wire_number']='102'
    if defect=='failure':result['success']=False
    with pytest.raises(RuntimeError):verify_wire_readback(link,entities,result,'101')
