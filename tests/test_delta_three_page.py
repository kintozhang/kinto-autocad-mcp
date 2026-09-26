import copy
import hashlib
from unittest.mock import patch
import pytest
from tests.test_delta_mapping import xml
from src.tools.trebi_batch import plan, execute
from src.tools import delta_batch

@pytest.fixture
def spec(tmp_path,monkeypatch):
    asset=tmp_path/'HBB1_KINTO_R2_EC0902_TEST.dwg';asset.write_bytes(b'fixture only')
    monkeypatch.setattr(delta_batch,'ASSET_SHA256',hashlib.sha256(asset.read_bytes()).hexdigest())
    esi=tmp_path/'esi.xml';esi.write_bytes(xml())
    mapping={'schema_version':2,'esi':{'path':str(esi),'sha256':hashlib.sha256(esi.read_bytes()).hexdigest()},
        'modules':[{'id':'IO_A','model':'R2-EC0902D0','input_mode':'PNP','observed_identity':None,'station':None}],
        'signals':[{'id':key,'target':{'module_id':'IO_A','port':port,'channel':0},'direction':direction,'purpose':'ordinary_control',
        'original':{'signal':'SYNTHETIC_'+key,'terminal':None,'page':None},'potential':'TEST_24V','wire_number':number,'plc_address':None,'evidence':['synthetic test fixture']}
        for key,port,direction,number in [('BUTTON',0,'input','TEST_DI'),('LAMP',2,'output','TEST_DO')]]}
    return {'schema_version':3,'recipe':'delta_di_do_three_page','purpose':'test_only','symbol_path':str(asset),'mapping':mapping,
        'manifest':{'schema_version':1,'entries':[{'id':s,'kind':'drawing','logical_page':s,'include_in_total':True,'drawing_file':s+'.dwg'} for s in ['102','300','405']]}}

def test_mapping_drives_three_page_plan_without_fabricating_plc_address(spec):
    result=plan(spec)
    assert result['pages']['effective_drawing_count']==3
    assert len(result['expected_references'])==4
    assert len(result['components'])==14 and len(result['connections'])==11
    assert not result['production_ready'] and not result['mapping']['mapping_complete']
    assert all(s['plc_address'] is None for s in result['mapping']['signals'])
    assert {s['wire_number'] for s in result['mapping']['signals']}=={'TEST_DI','TEST_DO'}
    components={c['id']:c for c in result['components']}
    for link in result['connections']:
        a,b=[components[link[s+'_id']] for s in ('from','to')]
        assert a['drawing_page']==b['drawing_page']
    assert components['r2']['attributes']['TAG1']=='-300A1'

@pytest.mark.parametrize('case',['production','channel','number','potential','safety','npn','missing_page','wrong_order','filename','revision'])
def test_invalid_mapping_never_contacts_cad(spec,case):
    if case=='production':spec['purpose']='production'
    if case=='channel':spec['mapping']['signals'][0]['target']['channel']=1
    if case=='number':spec['mapping']['signals'][0]['wire_number']='I545'
    if case=='potential':spec['mapping']['signals'][0]['potential']=None
    if case=='safety':spec['mapping']['signals'][0]['purpose']='safety'
    if case=='npn':spec['mapping']['modules'][0]['input_mode']='NPN'
    if case=='missing_page':spec['manifest']['entries'].pop()
    if case=='wrong_order':spec['manifest']['entries'].reverse()
    if case=='filename':spec['manifest']['entries'][0]['drawing_file']='../escape.dwg'
    if case=='revision':spec['mapping']['modules'][0]['observed_identity']={'vendor_id':'0x1dd','product_code':'0x902','revision':'0x99999999','source':'fixture'}
    with patch('src.autocad.connection.get_connection') as conn:
        result=execute('C:/test.wdp',spec,'C:/test.dwg')
    assert not result['success'] and not result['submitted']
    conn.assert_not_called()

