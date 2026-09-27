"""Report-derived junctions and signal-arrow paths must not be inferred from the recipe."""
from copy import deepcopy
import pytest
from src.tools.delta_path_acceptance import resolve_connector_network

@pytest.fixture
def branch_report():
    entities={};attrs={}
    for ident,handle,tag,pin,terminal in [('plug','A','-P','X1TERM01P','4'),('sensor','B','-B','X2TERM02','1'),('button','C','-S','X2TERM01','13')]:
        entities[ident]={'handle':handle,'connection_points':[{'connection':pin,'terminal':terminal}]}
        attrs[ident]={'TAG1':tag}
    rows=[]
    for h1,t1,p1,h2,t2,p2 in [('A','-P','4','B','-B','1'),('B','-B','1','C','-S','13')]:
        r=['']*50;r[0]='TEST24';r[2]=t1;r[3]=p1;r[5]=t2;r[6]=p2;r[7]=r[8]='TEST_24V';r[11]=r[12]='102';r[39]='h='+h1;r[40]='h='+h2;r[48]='h=D';r[49]='h=E';rows.append(r)
    return {'entities':entities,'references':attrs,'reports':{'from_to':{'rows':rows}},'final_wires':{'supply':{'connections':[('B','X2TERM02'),('C','X2TERM01')],'network_wire_handles':['D','E'],'wire_number':'TEST24','wire_layer':'TEST_24V'}}}

@pytest.mark.parametrize('fault',[None,'missing_branch','extra_device','wrong_pin','wrong_number','foreign_wire','disconnected','duplicate','unreported_raw'])
def test_branch_requires_actual_connected_report_evidence(branch_report,fault):
    r=branch_report;rows=r['reports']['from_to']['rows']
    if fault=='missing_branch':rows.pop()
    if fault=='extra_device':rows[1][40]='h=F'
    if fault=='wrong_pin':rows[1][6]='14'
    if fault=='wrong_number':rows[1][0]='TEST0'
    if fault=='foreign_wire':rows[1][49]='h=F'
    if fault=='disconnected':rows[1][39]='h=C';rows[1][2]='-S';rows[1][3]='13'
    if fault=='duplicate':rows.append(deepcopy(rows[0]))
    if fault=='unreported_raw':r['final_wires']['supply']['connections'].append(('F','X1TERM01'))
    call=lambda:resolve_connector_network({'id':'supply'},r,'102',{('plug','X1TERM01P'),('sensor','X2TERM02'),('button','X2TERM01')})
    if fault:
        with pytest.raises(ValueError):call()
    else:
        assert set(map(tuple,call()['connections']))=={('A','X1TERM01P'),('B','X2TERM02'),('C','X2TERM01')}

@pytest.fixture
def signal_report():
    comps=[{'id':'src','role':'source','signal_code':'SIG','drawing_page':'103'},{'id':'dst','role':'destination','signal_code':'SIG','drawing_page':'301'},
           {'id':'strip','drawing_page':'103'},{'id':'r2','drawing_page':'301'}]
    conns=[{'id':'to_arrow','from_id':'src','from_connection':'X1TERM01','to_id':'strip','to_connection':'X4TERM01','wire_number':'SIG'},
           {'id':'from_arrow','from_id':'dst','from_connection':'X1TERM01','to_id':'r2','to_connection':'X4TERM03','wire_number':'SIG'}]
    entities={'strip':{'handle':'CD1','connection_points':[{'connection':'X4TERM01','terminal':'I546'}]},
              'r2':{'handle':'A7B','connection_points':[{'connection':'X4TERM03','terminal':'TB2:X02'}]}}
    attrs={'strip':{'TAGSTRIP':'-X15'},'r2':{'TAG1':'-301A1'}}
    r=['']*50;r[0]='SIG';r[2]='-X15';r[3]='I546';r[5]='-301A1';r[6]='TB2:X02';r[7]=r[8]='L';r[11]='103';r[12]='301';r[39]='h=CD1';r[40]='h=A7B';r[48]='h=EC4';r[49]='h=C9F'
    wires={'to_arrow':{'network_wire_handles':['EC4'],'wire_number':'SIG','wire_layer':'L'},'from_arrow':{'network_wire_handles':['C9F'],'wire_number':'SIG','wire_layer':'L'}}
    return {'components':comps,'connections':conns},{'entities':entities,'references':attrs,'reports':{'from_to':{'rows':[r]}},'final_wires':wires}

@pytest.mark.parametrize('fault',[None,'missing','duplicate','wrong_pin','wrong_page','one_side_only','foreign_wire','wrong_number','no_pin_identity','unpaired'])
def test_signal_arrow_path_requires_single_native_cross_page_row(signal_report,fault):
    from src.tools.delta_path_acceptance import verify_signal_path
    recipe,r=signal_report;rows=r['reports']['from_to']['rows']
    if fault=='missing':rows.clear()
    if fault=='duplicate':rows.append(deepcopy(rows[0]))
    if fault=='wrong_pin':rows[0][6]='TB2:X01'
    if fault=='wrong_page':rows[0][12]='300'
    if fault=='one_side_only':rows[0][49]='h=EC4'
    if fault=='foreign_wire':rows[0][49]='h=FFF'
    if fault=='wrong_number':rows[0][0]='OTHER'
    if fault=='no_pin_identity':r['entities']['r2']['connection_points'][0]['terminal']=''
    if fault=='unpaired':recipe['components'].pop(1)
    call=lambda:verify_signal_path(recipe,r,'SIG')
    if fault:
        with pytest.raises(ValueError):call()
    else:
        assert call()['endpoints']==[('A7B','-301A1','TB2:X02','301'),('CD1','-X15','I546','103')]

def test_autoroute_branch_failure_retains_actual_geometry():
    from src.tools.circuit_blocks import select_branch_segment
    snapshots=[{'success':True,'wire_handle':'D','start':[197,200,0],'end':[278.5,200,0]}]
    assert select_branch_segment(snapshots,[240,200])=='D'
    with pytest.raises(ValueError,match='278.5'):select_branch_segment(snapshots,[280,200])

def test_device_fragments_do_not_allow_unqualified_symbols_or_pin_overrides():
    from src.tools.circuit_blocks import device
    with pytest.raises(ValueError):device('unknown','d','102',200,200,'-102B1',{})
    with pytest.raises(ValueError):device('sensor','d','102',200,200,'-102B1',{'TERM01':'1'})
    assert device('sensor','d','102',200,200,'-102B1',{})['attributes']['TERM01']=='4'

def test_duplicate_open_names_rejected_before_native_batch(tmp_path):
    from src.tools.circuit_blocks import validate_open_names
    a=str(tmp_path/'a'/'same.dwg');b=str(tmp_path/'b'/'same.dwg')
    with pytest.raises(ValueError,match='Duplicate'):validate_open_names([a,b],[b])
    validate_open_names([a,str(tmp_path/'other.dwg')],[a])
