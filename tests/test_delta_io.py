import copy,json
from pathlib import Path
import pytest
from src.tools.delta_io import plan

@pytest.fixture
def spec():
    return json.loads((Path(__file__).resolve().parents[1]/'examples/delta-r2-io-plan.json').read_text(encoding='utf8'))

def test_two_instances_and_input_output_common_are_distinct(spec):
    result=plan(spec);a,b,c=result['signals']
    assert a['endpoint']!=c['endpoint']
    assert a['common_terminal']=='TB3:S/S' and a['common_connection_draft']=='IO_0V'
    assert b['common_terminal']=='TB4:C0' and b['electrical_type']=='relay_no_dry_contact'
    assert a['object_index']=='0x6000' and b['object_index']=='0x6200'
    assert not result['ready_for_drawing'] and a['global_plc_address'] is None

def test_port_and_object_group_boundaries(spec):
    spec['signals']=[]
    for p in range(4):
        for ch in [0,7,8,15]:
            spec['signals'].append({'id':f'S{p}_{ch}','module_id':'IO_A','port':p,'channel':ch,'direction':'input' if p<2 else 'output','purpose':'ordinary_control','potential':'24V','source_signal':'TEST'})
    data=plan(spec)['signals']
    assert len({s['endpoint'] for s in data})==16
    assert [(s['subindex'],s['derived_bit_candidate']) for s in data[:8]]==[(1,0),(1,7),(2,0),(2,7),(3,0),(3,7),(4,0),(4,7)]
    assert data[-1]['common_terminal']=='TB5:C7'

@pytest.mark.parametrize('case',['duplicate_channel','duplicate_id','unknown_module','wrong_model','direction','safety','channel','port_bool','mixed_potential','global_address','per_port_input_mode'])
def test_rejects_invalid_or_ambiguous_mapping(spec,case):
    if case=='duplicate_channel':spec['signals'].append({**spec['signals'][0],'id':'DUP'})
    if case=='duplicate_id':spec['signals'][2]['id']='input_test'
    if case=='unknown_module':spec['signals'][0]['module_id']='UNKNOWN'
    if case=='wrong_model':spec['modules'][0]['model']='R2-EC0004'
    if case=='direction':spec['signals'][1]['direction']='input'
    if case=='safety':spec['signals'][0]['purpose']='emergency_stop'
    if case=='channel':spec['signals'][0]['channel']=16
    if case=='port_bool':spec['signals'][0]['port']=True
    if case=='mixed_potential':spec['signals'].append({**spec['signals'][1],'id':'DO2','channel':1,'potential':'OTHER_SUPPLY'})
    if case=='global_address':spec['signals'][0]['global_plc_address']='X100'
    if case=='per_port_input_mode':spec['signals'][0]['input_mode']='NPN'
    with pytest.raises(ValueError):plan(spec)
