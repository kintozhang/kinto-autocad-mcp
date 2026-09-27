from copy import deepcopy
import pytest
from tests.test_delta_mapping import spec
from src.tools.delta_io import plan


def wrap(spec, start=256):
    return {'schema_version': 4, 'purpose': 'test_only', 'mapping': spec,
            'eio_assumptions': [{'module_id': 'IO_A', 'eio_sequence': 1,
                                'eio_port': 501, 'start_address': start, 'source': 'test assumption'}]}


def test_manual_example_and_no_promotion(spec):
    before = deepcopy(spec)
    out = plan(wrap(spec))
    assert out['candidates'][0]['nc50_address_candidate'] == 'Y256'
    assert out['mapping']['signals'][0]['global_plc_address'] is None
    assert out['mapping']['module_evidence']['io_a']['station'] is None
    assert spec == before
    assert out['test_plan_valid'] and not out['formal_export_allowed']
    assert not out['cad_contacted'] and not out['hardware_contacted']


@pytest.mark.parametrize('port,ch,expected', [(0,0,'X256'),(0,15,'X271'),(1,0,'X272'),(1,15,'X287'),(2,0,'Y256'),(2,15,'Y271'),(3,0,'Y272'),(3,15,'Y287')])
def test_all_port_edges(spec, port, ch, expected):
    spec['signals'][0]['target'].update(port=port, channel=ch)
    spec['signals'][0]['direction'] = 'input' if port < 2 else 'output'
    assert plan(wrap(spec))['candidates'][0]['nc50_address_candidate'] == expected


@pytest.mark.parametrize('field,value', [('start_address',481),('start_address',255),('start_address',True),('eio_port',0),('eio_port',521),('eio_sequence',0)])
def test_invalid_configuration(spec, field, value):
    s=wrap(spec);s['eio_assumptions'][0][field]=value
    with pytest.raises(ValueError): plan(s)


def test_update_candidate_preserves_origin(spec):
    a=plan(wrap(spec));b=plan(wrap(spec,288))
    assert b['candidates'][0]['nc50_address_candidate']=='Y288'
    for field in ['original','physical_endpoint','wire_number','potential','pdo_candidate']:
        assert a['candidates'][0][field]==b['candidates'][0][field]
    assert b['mapping']['signals'][0]['plc_address'] is None


@pytest.mark.parametrize('case', ['overlap','duplicate_port','duplicate_sequence','duplicate_module'])
def test_multi_module_conflicts(spec,case):
    spec['modules'].append({**spec['modules'][0],'id':'IO_B'})
    s=wrap(spec);s['eio_assumptions'].append({'module_id':'IO_B','eio_sequence':2,'eio_port':502,'start_address':288,'source':'test'})
    row=s['eio_assumptions'][1]
    if case=='overlap':row['start_address']=287
    if case=='duplicate_port':row['eio_port']=501
    if case=='duplicate_sequence':row['eio_sequence']=1
    if case=='duplicate_module':row['module_id']='io_a'
    with pytest.raises(ValueError):plan(s)


def test_last_valid_module_and_explicit_conflict(spec):
    spec['signals'][0]['target'].update(port=3,channel=15)
    spec['signals'][0]['plc_address']={'value':'Y999','source':'deliberately conflicting fixture'}
    out=plan(wrap(spec,480))
    assert out['candidates'][0]['nc50_address_candidate']=='Y511'
    assert not out['test_plan_valid'] and out['conflicting_explicit_addresses']==['LAMP']
    assert out['mapping']['signals'][0]['global_plc_address']=='Y999'


def test_production_rejected(spec):
    s=wrap(spec);s['purpose']='production'
    with pytest.raises(ValueError):plan(s)
