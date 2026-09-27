import copy
from unittest.mock import patch
import pytest
from tests.test_delta_three_page import spec as base_spec
from src.tools.trebi_batch import plan, execute

@pytest.fixture
def sensor_spec(base_spec):
    mapping = copy.deepcopy(base_spec['mapping'])
    signal = mapping['signals'][0]
    signal.update(id='SENSOR', original={'signal':'I546','terminal':'-300A2:3','page':'102'}, wire_number='TEST_I546')
    signal['target']['channel'] = 1
    mapping['signals'] = [signal]
    routes = []
    for role, original, core, pin, terminal, number, layer in [
        ('sensor_supply','24IE','1','4','1','TEST24','TEST_24V'),
        ('sensor_return','0V','2','5','3','TEST0','TEST_0V'),
        ('sensor_signal','I546','4','7','4','TEST_I546','TEST_SIGNAL')]:
        routes.append(dict(id=role, original=original, strip='-XTEST', terminal=original, cable='-WTEST', core=core,
            socket='-JTEST',plug='-PTEST',socket_pin=pin,plug_pin=pin,device='-102B1',device_terminal=terminal,
            wire_number=number,wire_layer=layer,source='synthetic fixture'))
    manifest=copy.deepcopy(base_spec['manifest']);manifest['entries'].pop()
    return dict(schema_version=5,recipe='remote_io_sensor_paths',purpose='test_only',manifest=manifest,mapping=mapping,routes=routes,
        sensor=dict(tag='-102B1',symbol='VPX11IN3',test_input_mode='PNP',hardware_model=None,hardware_output_type=None,source='synthetic fixture'))

def test_sensor_plan_keeps_original_channel_and_address_separate(sensor_spec):
    p=plan(sensor_spec)
    assert p['target_endpoint']['electrical_connection']=='X4TERM02'
    assert p['target_endpoint']['terminal']=='X01'
    assert p['target_endpoint']['derived_bit_candidate']==1
    assert p['mapping']['signals'][0]['original']['terminal']=='-300A2:3'
    assert p['mapping']['signals'][0]['global_plc_address'] is None
    assert p['input_common']['test_potential']=='TEST_0V'
    assert not any(p[k] for k in ('cad_contacted','submitted','execution_supported','production_ready','formal_export_allowed'))

def test_unqualified_sensor_execute_never_contacts_cad(sensor_spec):
    with patch('src.autocad.connection.get_connection') as conn:
        result=execute('C:/fixture.wdp',sensor_spec,'C:/fixture.dwg')
    assert result['status']=='qualification_required' and not result['submitted']
    conn.assert_not_called()

@pytest.mark.parametrize('case',['missing','swapped_supply','core','pin','mate','same_halves','tag_collision','signal_as_address','output_port','out_of_range','safety','npn','model','production','page','filename','revision','mapping_version'])
def test_sensor_rejects_invalid_mapping_before_cad(sensor_spec,case):
    s=sensor_spec;r=s['routes'];signal=s['mapping']['signals'][0]
    if case=='missing':r.pop()
    if case=='swapped_supply':r[0]['device_terminal']='3'
    if case=='core':r[2]['core']='3'
    if case=='pin':r[2].update(socket_pin='6',plug_pin='6')
    if case=='mate':r[2]['plug_pin']='8'
    if case=='same_halves':
        for row in r:row['plug']=row['socket']
    if case=='tag_collision':
        for row in r:row['cable']=row['strip']
    if case=='signal_as_address':signal['wire_number']='X289'
    if case=='output_port':signal['target']['port']=2
    if case=='out_of_range':signal['target']['channel']=16
    if case=='safety':signal['purpose']='safety'
    if case=='npn':s['mapping']['modules'][0]['input_mode']='NPN'
    if case=='model':s['sensor']['symbol']='FAKE'
    if case=='production':s['purpose']='production'
    if case=='page':s['manifest']['entries'][0]['logical_page']='103'
    if case=='filename':s['manifest']['entries'][0]['drawing_file']='../outside.dwg'
    if case=='revision':s['mapping']['modules'][0]['observed_identity']={'vendor_id':'0x1dd','product_code':'0x902','revision':'0x99999999','source':'fixture'}
    if case=='mapping_version':s['mapping']['schema_version']=1
    with patch('src.autocad.connection.get_connection') as conn:
        result=execute('C:/fixture.wdp',s,'C:/fixture.dwg')
    assert not result['success'] and not result['submitted']
    conn.assert_not_called()

def test_executable_sensor_uses_shared_circuit_fragments(sensor_spec, base_spec):
    sensor_spec['execution']={'symbol_path':base_spec['symbol_path'],'shared_loads':True}
    p=plan(sensor_spec)
    assert p['execution_supported'] and p['native_path_acceptance']
    assert len(p['cable_markers'])==3
    assert len(p['connections'])==16
    assert len([w for w in p['connections'] if w.get('kind')=='branch'])==2
    assert next(w for w in p['connections'] if w['id']=='module_input')['to_connection']=='X4TERM02'
    assert next(c for c in p['components'] if c['id']=='di_dst')['y']==235
    assert not p['production_ready']

def test_sensor_pages_tags_and_channel_are_configuration(sensor_spec,base_spec):
    sensor_spec['execution']={'symbol_path':base_spec['symbol_path'],'shared_loads':False}
    for row,page in zip(sensor_spec['manifest']['entries'],['103','301']):
        row.update(logical_page=page,drawing_file=page+'.dwg')
    sensor_spec['sensor']['tag']='-103B2'
    for r in sensor_spec['routes']:r['device']='-103B2'
    sensor_spec['mapping']['signals'][0]['target']['channel']=2
    p=plan(sensor_spec)
    assert {c['drawing_page'] for c in p['components']}=={'103','301'}
    assert next(c for c in p['components'] if c['id']=='r2')['attributes']['TAG1']=='-301A1'
    assert next(c for c in p['components'] if c['id']=='sensor')['attributes']['TAG1']=='-103B2'
    assert next(w for w in p['connections'] if w['id']=='module_input')['to_connection']=='X4TERM03'
    assert not any(w.get('kind')=='branch' for w in p['connections'])

@pytest.mark.parametrize('fault',['bad_asset','unsupported_channel','string_flag','extra_field'])
def test_executable_sensor_rejects_before_cad(sensor_spec,base_spec,fault):
    sensor_spec['execution']={'symbol_path':base_spec['symbol_path'],'shared_loads':True}
    if fault=='bad_asset':sensor_spec['execution']['symbol_path']='C:/missing.dwg'
    if fault=='unsupported_channel':sensor_spec['mapping']['signals'][0]['target']['channel']=15
    if fault=='string_flag':sensor_spec['execution']['shared_loads']='true'
    if fault=='extra_field':sensor_spec['execution']['unsafe']='ignored'
    with patch('src.autocad.connection.get_connection') as conn:r=execute('C:/fixture.wdp',sensor_spec,'C:/fixture.dwg')
    assert not r['success'] and not r['submitted']
    conn.assert_not_called()

@pytest.mark.parametrize('fault',['foreign_target','wrong_branch_number','cross_page','duplicate_cable_tag','duplicate_terminal','out_of_frame'])
def test_assembled_circuit_rejects_invalid_fragments(sensor_spec,base_spec,fault):
    from src.tools.circuit_blocks import validate_circuit
    sensor_spec['execution']={'symbol_path':base_spec['symbol_path'],'shared_loads':True}
    p=plan(sensor_spec);branch=next(w for w in p['connections'] if w.get('kind')=='branch')
    if fault=='foreign_target':branch['target_wire']='module_input'
    if fault=='wrong_branch_number':branch['wire_number']='TEST0'
    if fault=='cross_page':next(c for c in p['components'] if c['id']=='sensor')['drawing_page']='300'
    if fault=='duplicate_cable_tag':p['cable_markers'][0]['attributes']['TAG1']='-300A1'
    if fault=='duplicate_terminal':next(c for c in p['components'] if c['id']=='lamp_boundary')['attributes']['TERM01']='BUTTON'
    if fault=='out_of_frame':p['components'][0]['x']=999
    with pytest.raises(ValueError):validate_circuit(p['components'],p['connections'],p['cable_markers'])
