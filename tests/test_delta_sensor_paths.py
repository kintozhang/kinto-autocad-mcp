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
