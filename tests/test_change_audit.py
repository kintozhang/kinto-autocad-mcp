from copy import deepcopy
import pytest
from src.autocad.change_audit import verify

def fixture():
    before={'AA':{'type':'AcDbBlockReference','name':'HLT1G','layer':'SYMS','position':[150,200,0],
        'attributes':{'COLOR':'GN','CAT':'LAMP_24V_TEST','TAG1':'-405H1'}},
        'BB':{'type':'AcDbLine','layer':'TEST_SIGNAL','start':[50,200,0],'end':[142.5,200,0]}}
    after=deepcopy(before);after['CC']=after.pop('AA');after['CC']['name']='HLT1R';after['CC']['attributes'].update(COLOR='RD',CAT='LAMP_24V_RED_TEST')
    return before,after,{'action':'lamp_green_to_red','component_handle':'aa'},{'new_handle':'cc'}

def test_exact_replacement_and_inputs_not_modified():
    before,after,spec,report=fixture();original=deepcopy((before,after))
    assert verify(before,after,spec,report)['unrelated_objects_unchanged']
    assert (before,after)==original

@pytest.mark.parametrize('case',['extra_line','wire_moved','wrong_tag','lamp_moved','wrong_layer','missing_wire'])
def test_unexpected_changes_rejected(case):
    before,after,spec,report=fixture()
    if case=='extra_line':after['DD']=deepcopy(after['BB'])
    if case=='wire_moved':after['BB']['end'][0]=140
    if case=='wrong_tag':after['CC']['attributes']['TAG1']='-405H2'
    if case=='lamp_moved':after['CC']['position'][0]=170
    if case=='wrong_layer':after['CC']['layer']='0'
    if case=='missing_wire':after.pop('BB')
    with pytest.raises(RuntimeError):verify(before,after,spec,report)


def channel_fixture():
    def line():
        return {'type': 'AcDbLine', 'layer': 'TEST_SIGNAL',
                'start': [200, 235, 0], 'end': [225, 235, 0]}
    number = {'type': 'AcDbBlockReference', 'name': 'WD_WNH',
              'layer': 'WIRENO', 'attributes': {'WIRENO': 'TEST_DO'}}
    before = {
        'AA': {'type': 'AcDbBlockReference', 'name': 'R2', 'layer': 'SYMS',
               'attributes': {'X1TERM33': 'TEST_DO', 'X1TERM34': '',
                              'TERM33': 'TB4:Y00', 'TERM34': 'TB4:Y01',
                              'TERM01': 'COM', 'TAG1': '-300A1'}},
        'BB': line(), 'CC': deepcopy(number), 'DD': line(),
    }
    after = deepcopy(before)
    after.pop('BB'); after.pop('CC')
    after['AA']['attributes'].update(X1TERM33='', X1TERM34='TEST_DO')
    after.update({h: line() for h in ['E1', 'E2', 'E3']})
    after['E4'] = number
    spec = {'action': 'output_y00_to_y01', 'component_handle': 'aa', 'wire_handles': ['bb']}
    report = {'before_wires': [{'number_block_handle': 'cc'}],
              'new_wire': {'wire_handles': ['e1', 'e2', 'e3']}}
    return before, after, spec, report


def test_channel_allowlist_and_inputs_not_modified():
    before, after, spec, report = channel_fixture()
    original = deepcopy((before, after, spec, report))
    assert verify(before, after, spec, report)['unrelated_objects_unchanged']
    assert (before, after, spec, report) == original


@pytest.mark.parametrize('case', [
    'common_terminal_changed', 'old_pin_not_cleared', 'new_pin_wrong',
    'unrelated_wire_removed', 'extra_object', 'wrong_wire_layer',
    'wrong_wire_type', 'wrong_number', 'wrong_number_layer',
    'duplicate_route_handles', 'too_few_segments',
])
def test_channel_unexpected_changes_rejected(case):
    before, after, spec, report = channel_fixture()
    if case == 'common_terminal_changed': after['AA']['attributes']['TERM01'] = 'OTHER'
    if case == 'old_pin_not_cleared': after['AA']['attributes']['X1TERM33'] = 'TEST_DO'
    if case == 'new_pin_wrong': after['AA']['attributes']['X1TERM34'] = 'OTHER'
    if case == 'unrelated_wire_removed': after.pop('DD')
    if case == 'extra_object': after['FF'] = deepcopy(after['DD'])
    if case == 'wrong_wire_layer': after['E1']['layer'] = '0'
    if case == 'wrong_wire_type': after['E1']['type'] = 'AcDbCircle'
    if case == 'wrong_number': after['E4']['attributes']['WIRENO'] = 'OTHER'
    if case == 'wrong_number_layer': after['E4']['layer'] = '0'
    if case == 'duplicate_route_handles': report['new_wire']['wire_handles'] = ['E1', 'e1', 'E3']
    if case == 'too_few_segments': report['new_wire']['wire_handles'] = ['E1', 'E2']
    with pytest.raises(RuntimeError):
        verify(before, after, spec, report)


def test_unknown_action_rejected_even_for_valid_channel_diff():
    before, after, spec, report = channel_fixture()
    spec['action'] = 'unknown_action'
    with pytest.raises(ValueError, match='Unsupported'):
        verify(before, after, spec, report)
