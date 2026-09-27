import copy
import pytest
from unittest.mock import patch
from tests.test_delta_three_page import spec as three_page_spec
from src.tools.trebi_batch import plan,execute
from src.tools.delta_full_paths import validate_routes

@pytest.fixture
def spec(three_page_spec):
    s=copy.deepcopy(three_page_spec);s.update(schema_version=4,recipe='remote_io_button_lamp_paths')
    s['manifest']['entries'].pop()
    s['routes']=[dict(id=role,original=signal,strip='-XTEST',terminal=signal,cable='-WTEST',core=core,socket='-JTEST',plug='-PTEST',socket_pin=pin,plug_pin=pin,device='-102S1',device_terminal=terminal,source='synthetic fixture') for role,signal,core,pin,terminal in [('button_supply','TEST24','1','4','13'),('button_return','SYNTHETIC_BUTTON','3','6','14'),('lamp_feed','SYNTHETIC_LAMP','9','12','1'),('lamp_return','TEST0','2','5','2')]]
    s['binding']={'controller':'NC50E-FE','protocol':'EtherCAT','ss_potential':'TEST_0V','output_common_potential':'TEST_24V','source':'synthetic PNP/common wiring','observations':{'BUTTON':None,'LAMP':None}}
    return s

def test_default_dispatch_full_paths_and_unknown_binding(spec):
    p=plan(spec)
    assert len(p['routes'])==4 and len(p['cable_markers'])==4
    assert len([c for c in p['components'] if c['role']=='connector_half'])==2
    assert len(p['connections'])==17
    assert not p['formal_export_allowed'] and not p['production_ready']
    assert any('PDO' in x for x in p['binding']['pending'])
    assert {s['global_plc_address'] for s in p['mapping']['signals']}=={None}

@pytest.mark.parametrize('case',['missing','core','pin','mate','same_halves','wrong_device_pin','signal','ss','c0','channel','production','pdo','address','builtin_tag'])
def test_bad_full_paths_rejected_before_cad(spec,case):
    if case=='builtin_tag':
        for route in spec['routes']:route['socket']='-300A1'
    if case=='missing':spec['routes'].pop()
    if case=='core':spec['routes'][1]['core']='1'
    if case=='pin':spec['routes'][1].update(socket_pin='4',plug_pin='4')
    if case=='mate':spec['routes'][1]['plug_pin']='999'
    if case=='same_halves':spec['routes'][0]['plug']=spec['routes'][0]['socket']
    if case=='wrong_device_pin':spec['routes'][0]['device_terminal']='14'
    if case=='signal':spec['routes'][1]['original']='WRONG'
    if case=='ss':spec['binding']['ss_potential']='TEST_24V'
    if case=='c0':spec['binding']['output_common_potential']='TEST_0V'
    if case=='channel':spec['mapping']['signals'][0]['target']['channel']=1
    if case=='production':spec['purpose']='production'
    if case in {'pdo','address'}:
        spec['binding']['observations']['BUTTON']={'object_index':'0x6000','subindex':1,'bit':1 if case=='pdo' else 0,'plc_address':'NC50_UNKNOWN','source':'fixture'}
    with patch('src.autocad.connection.get_connection') as conn:
        result=execute('C:/fixture.wdp',spec,'C:/fixture.dwg')
    assert not result['success'] and result['submitted'] is False
    conn.assert_not_called()

def test_matching_declared_pdo_does_not_claim_hardware(spec):
    spec['mapping']['signals'][0]['plc_address']={'value':'EXPLICIT_TEST_ADDRESS','source':'fixture'}
    spec['binding']['observations']['BUTTON']={'object_index':'0x6000','subindex':1,'bit':0,'plc_address':'EXPLICIT_TEST_ADDRESS','source':'fixture'}
    p=plan(spec)
    assert p['binding']['checks'][0]['hardware_contacted'] is False
    assert p['binding']['pending'] and not p['production_ready']


def native_receipt(spec):
    from src.tools.delta_module_inventory import expected_smart_symbol_connections
    from collections import defaultdict
    p=plan(spec);r={'entities':{},'references':{},'device_inventory':{'102':[],'300':[]},'final_wires':{},'reports':{k:{'success':True,'rows':[]} for k in ('bom','from_to','terminal_plan','terminal_numbers')}}
    for i,c in enumerate(p['components']+p['cable_markers']):
        a=dict(c['attributes']);points=[]
        if c['id']=='r2':points=[{'connection':k,'terminal':v} for k,v in expected_smart_symbol_connections().items()]
        if c['role']=='connector_half':
            prefix,suffix=('X1','P') if c['side']=='plug' else ('X4','J')
            points=[{'connection':f'{prefix}TERM{j+1:02d}{suffix}','terminal':pin} for j,pin in enumerate(c['pins'])]
            a.update({f'TERM{j+1:02d}{suffix}':pin for j,pin in enumerate(c['pins'])})
        h=f'{i+1:X}';r['entities'][c['id']]={'handle':h,'drawing':c['drawing_page'],'connection_points':points};r['references'][c['id']]=a
        if any(a.get(k) for k in ('TAG1','TAG2','TAGSTRIP')):r['device_inventory'][c['drawing_page']].append({'handle':h,'attributes':a})
        if 'CAT' in a:
            row=['']*16;row[1]='1';row[3]=a['CAT'];row[4]=a['MFG'];row[15]=a['TAG1'];r['reports']['bom']['rows'].append(row)
    for ref in p['expected_references']:r['references'][ref['id']][ref['field']]=ref['value']
    graph=defaultdict(set)
    def node(id,pin):return (r['entities'][id]['handle'],pin)
    for w in p['connections']:
        a=node(w['from_id'],w['from_connection']);b=node(w['to_id'],w['to_connection']);graph[a].add(b);graph[b].add(a)
    for w in p['connections']:
        todo=[node(w['from_id'],w['from_connection'])];seen=set()
        while todo:
            n=todo.pop()
            if n not in seen:seen.add(n);todo.extend(graph[n]-seen)
        r['final_wires'][w['id']]={'success':True,'connections':list(seen),'wire_layer':w['wire_layer'],'wire_number':w['wire_number']}
    for route in p['routes']:
        row=['']*15;row[2]=route['strip'];row[3]=route['terminal'];row[5]=route['socket'];row[6]=route['socket_pin'];row[13]=route['cable'];row[14]=route['core'];r['reports']['from_to']['rows'].append(row)
        row=['']*15;row[2]=route['plug'];row[3]=route['plug_pin'];row[5]=route['device'];row[6]=route['device_terminal'];r['reports']['from_to']['rows'].append(row)
        row=['']*13;row[10]=route['strip'];row[12]=route['terminal'];r['reports']['terminal_plan']['rows'].append(row)
    for i,w in enumerate(p['connections']):
        if not {'socket','plug'}.intersection({w['from_id'],w['to_id']}):continue
        ends=[]
        for side in ('from','to'):
            id=w[side+'_id'];a=r['references'][id];pin=w[side+'_connection']
            point=next((pt for pt in r['entities'][id]['connection_points'] if pt['connection']==pin),None)
            if point is None:
                terminal=a.get('TERM'+pin[6:]) or a.get('TERM01')
                point={'connection':pin,'terminal':terminal};r['entities'][id]['connection_points'].append(point)
            ends.append((a.get('TAG1') or a.get('TAGSTRIP'),point['terminal']))
        row=next(row for row in r['reports']['from_to']['rows'] if {(row[2],row[3]),(row[5],row[6])}==set(ends))
        row.extend(['']*(50-len(row)))
        row[0]=w['wire_number'];row[7]=row[8]=w['wire_layer'];row[11]=row[12]='102'
        row[39]='h='+r['entities'][w['from_id']]['handle'];row[40]='h='+r['entities'][w['to_id']]['handle']
        row[48]=row[49]='h='+f'{256+i:X}'
        r['final_wires'][w['id']]['network_wire_handles']=[f'{256+i:X}']
    r['reports']['terminal_numbers']['rows']=[['fixture']]
    return p,r


def test_native_complete_contract(spec):
    from src.tools.delta_path_acceptance import verify_native
    p,r=native_receipt(spec)
    assert verify_native(p,r)['routes']==4

@pytest.mark.parametrize('fault',['short','missing_wire','wrong_wire_number','missing_pin','changed_pin','wrong_core','wrong_socket','missing_field','extra_device','missing_r2_point','bom_quantity','terminal_report','xref','cable_xref'])
def test_native_acceptance_detects_wrong_saved_data(spec,fault):
    from src.tools.delta_path_acceptance import verify_native
    p,r=native_receipt(spec)
    if fault=='short':r['final_wires']['field_button_supply']['connections'].append(('FFFF','X1TERM01'))
    if fault=='missing_wire':r['final_wires'].pop('field_button_supply')
    if fault=='wrong_wire_number':r['final_wires']['field_button_supply']['wire_number']='TEST0'
    if fault=='missing_pin':r['entities']['socket']['connection_points'].pop()
    if fault=='changed_pin':r['references']['plug']['TERM01P']='999'
    if fault=='wrong_core':r['reports']['from_to']['rows'][0][14]='999'
    if fault=='wrong_socket':r['reports']['from_to']['rows'][0][5]='-OTHER'
    if fault=='missing_field':r['reports']['from_to']['rows'].pop(1)
    if fault=='extra_device':r['device_inventory']['102'].append({'handle':'FFFF','attributes':{'TAG1':'DUP'}})
    if fault=='missing_r2_point':r['entities']['r2']['connection_points'].pop()
    if fault=='bom_quantity':r['reports']['bom']['rows'][0][1]='2'
    if fault=='terminal_report':r['reports']['terminal_plan']['rows'].pop()
    if fault=='cable_xref':r['references']['core_lamp_feed']['XREF']='102.9'
    if fault=='xref':r['references']['di_src']['XREF']='300.9'
    with pytest.raises((ValueError,KeyError,RuntimeError)):verify_native(p,r)


def test_unified_audit_automatically_loads_p0_and_blocks_unknown_hardware(spec,tmp_path):
    import json
    from src.tools.project_acceptance import audit
    from src.autocad.engineering_archive import digest
    project=tmp_path/'project.wdp';project.write_text('102.dwg\n300.dwg\n')
    for name in ['102.dwg','300.dwg']:(tmp_path/name).write_bytes(b'fixture')
    subjects=audit(project,[])['subjects'];p,r=native_receipt(spec)
    r.update(spec=spec,subjects=subjects,status='native_readback_verified',success=True)
    receipt=tmp_path/'receipt.json';receipt.write_text(json.dumps(r),encoding='utf8')
    sidecar=project.with_suffix('.p0.json');sidecar.write_text(json.dumps({'schema_version':1,'kind':'p0_paths','subjects':subjects,'receipt_path':str(receipt),'receipt_sha256':digest(receipt)}),encoding='utf8')
    result=audit(project,[])
    assert result['p0_paths']['success'] and not result['evidence_complete']
    assert {'tag_uniqueness','connections','cross_references','bom','terminals'} <= set(result['accepted'])
    assert 'save_reopen' not in result['accepted']
    assert any(b.get('category')=='p0_binding' and 'NC50' in b['reason'] for b in result['blockers'])
    (tmp_path/'102.dwg').write_bytes(b'changed drawing')
    assert audit(project,[])['p0_paths'] is None
    assert not audit(project,[])['accepted']
    assert 'modified project' in str(audit(project,[])['blockers'])

@pytest.mark.parametrize('fault',[None,'foreign_segment','foreign_handle','extra_row','missing_membership','foreign_raw_endpoint','foreign_page'])
def test_connector_report_resolution_requires_independent_native_handles(spec,fault):
    from src.tools.delta_path_acceptance import verify_native
    p,r=native_receipt(spec);wire=r['final_wires']['cable_button_supply'];wire['connections']=wire['connections'][:1]
    row=r['reports']['from_to']['rows'][0]
    if fault=='foreign_page':row[11]=row[12]='300'
    if fault=='foreign_segment':row[49]='h=FFFF'
    if fault=='foreign_handle':row[40]='h=FFFF'
    if fault=='extra_row':r['reports']['from_to']['rows'].append(list(row))
    if fault=='missing_membership':wire.pop('network_wire_handles')
    if fault=='foreign_raw_endpoint':wire['connections'].append(('FFFF','X1TERM01'))
    if fault is None:assert verify_native(p,r)['success']
    else:
        with pytest.raises((ValueError,RuntimeError)):verify_native(p,r)


def test_nc50_test_annotations_and_no_observation_promotion(spec):
    spec['eio_assumptions']=[{'module_id':spec['mapping']['modules'][0]['id'],'eio_sequence':1,'eio_port':501,'start_address':256,'source':'test'}]
    p=plan(spec)
    attrs={c['id']:c['attributes'] for c in p['components']}
    assert attrs['button']['DESC2']=='TEST NC50 X256'
    assert attrs['lamp']['DESC2']=='TEST NC50 Y256'
    assert attrs['r2']['DESC3']=='NC50 X256 / Y256'
    assert all(s['global_plc_address'] is None for s in p['mapping']['signals'])
    assert p['binding']['pending'] and not p['formal_export_allowed']


def test_nc50_bad_range_rejects_batch_before_cad(spec):
    spec['eio_assumptions']=[{'module_id':spec['mapping']['modules'][0]['id'],'eio_sequence':1,'eio_port':501,'start_address':481,'source':'test'}]
    with patch('src.autocad.connection.get_connection') as conn:
        out=execute('C:/fixture.wdp',spec,'C:/fixture.dwg')
    assert not out['success'] and not out['submitted']
    conn.assert_not_called()


@pytest.mark.parametrize('fault',[None,'missing_row','wrong_description','wrong_handle','symbol_default'])
def test_candidate_bom_is_native_and_exact(spec,fault):
    from src.tools.delta_path_acceptance import verify_native
    spec['eio_assumptions']=[{'module_id':spec['mapping']['modules'][0]['id'],'eio_sequence':1,'eio_port':501,'start_address':256,'source':'test'}]
    p,r=native_receipt(spec)
    for row in r['reports']['bom']['rows']:
        c=next(c for c in p['components']+p['cable_markers'] if c['attributes'].get('CAT')==row[3])
        row.extend(['']*(27-len(row)))
        row[16:19]=[c['attributes'].get(k,'') for k in ('DESC1','DESC2','DESC3')]
        row[22]='h='+r['entities'][c['id']]['handle']
    row=next(row for row in r['reports']['bom']['rows'] if row[3]=='LAMP_24V_TEST')
    if fault=='symbol_default':
        r['references']['r2']['DESC1']='R2-EC0902D0'
        next(x for x in r['reports']['bom']['rows'] if x[3]=='R2-EC0902D0')[16]='R2-EC0902D0'
    if fault=='missing_row':r['reports']['bom']['rows'].remove(row)
    if fault=='wrong_description':row[17]='TEST NC50 Y288'
    if fault=='wrong_handle':row[22]='h=FFFF'
    if fault and fault!='symbol_default':
        with pytest.raises(ValueError):verify_native(p,r)
    else:assert verify_native(p,r)['routes']==4

@pytest.mark.parametrize('fault',[None,'missing','different_version','bad_reopened_wire'])
def test_v5_audit_requires_independent_reopen_snapshot(spec,tmp_path,fault):
    import json
    from src.tools.delta_path_acceptance import review_evidence
    from src.autocad.engineering_archive import digest
    p,r=native_receipt(spec)
    snapshot=copy.deepcopy(r)
    r.update(spec={**spec,'schema_version':5},subjects={'fixture':'hash'},status='native_readback_verified',success=True,save_reopen='verified')
    r['independent_reopen']={'success':True,'subjects':r['subjects'],'snapshot':snapshot}
    if fault=='missing':r.pop('independent_reopen')
    if fault=='different_version':r['independent_reopen']['subjects']={}
    if fault=='bad_reopened_wire':snapshot['final_wires']['module_input']['connections'].append(('FFFF','X1TERM01'))
    source=tmp_path/'receipt.json';source.write_text(json.dumps(r),encoding='utf8')
    data={'schema_version':1,'subjects':r['subjects'],'receipt_path':str(source),'receipt_sha256':digest(source)}
    # Isolate the version-bound evidence check from layout planning.
    with patch('src.tools.trebi_batch.plan',return_value=p):
        if fault:
            with pytest.raises((ValueError,RuntimeError)):review_evidence(data,r['subjects'])
        else:
            assert 'save_reopen' in review_evidence(data,r['subjects'])['verified_categories']
