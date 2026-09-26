import hashlib
import pytest
from src.tools.delta_io import plan
from src.autocad.delta_esi import inspect_esi

def xml(revision='00100000'):
    parts=[]
    for tag,idx,obj,sm in [('RxPdo','1600','6200',2),('TxPdo','1A00','6000',3)]:
        entries=''.join(f'<Entry><Index>#x{obj}</Index><SubIndex>{s}</SubIndex><BitLen>8</BitLen></Entry>' for s in range(1,5))
        parts.append(f'<{tag} Mandatory="1" Sm="{sm}"><Index>#x{idx}</Index>{entries}</{tag}>')
    return ('<EtherCATInfo><Vendor><Id>#x01DD</Id></Vendor><Descriptions><Devices><Device>'
            f'<Type ProductCode="#x00000902" RevisionNo="#x{revision}">R2-EC0902</Type>'
            +''.join(parts)+'</Device></Devices></Descriptions></EtherCATInfo>').encode()

@pytest.fixture
def spec(tmp_path):
    p=tmp_path/'synthetic.xml';p.write_bytes(xml())
    return {'schema_version':2,'esi':{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},
        'modules':[{'id':'IO_A','model':'R2-EC0902D0','input_mode':'PNP','observed_identity':None,'station':None}],
        'signals':[{'id':'LAMP','target':{'module_id':'IO_A','port':2,'channel':0},'direction':'output',
                    'purpose':'ordinary_control','original':{'signal':'ORIGINAL_OUTPUT','terminal':None,'page':None},
                    'potential':None,'wire_number':None,'plc_address':None,'evidence':[]}]}

def identity(rev='0x00100000'):
    return {'vendor_id':'0x01dd','product_code':'0x902','revision':rev,'source':'synthetic readback fixture'}

def test_unknown_fields_remain_unknown(spec):
    out=plan(spec);s=out['signals'][0]
    assert out['esi']['status']=='parsed_basic_pdo_verified'
    assert not out['mapping_complete'] and not out['ready_for_drawing']
    assert s['terminal']=='Y00' and s['original']['signal']=='ORIGINAL_OUTPUT'
    assert s['potential'] is None and s['wire_number'] is None and s['global_plc_address'] is None
    assert s['common_connection_draft'] is None

@pytest.mark.parametrize('rev',['0x00100000','0x01100000'])
def test_exact_revision_match(spec,rev):
    p=spec['esi']['path'];raw=xml(rev[2:])
    from pathlib import Path
    Path(p).write_bytes(raw);spec['esi']['sha256']=hashlib.sha256(raw).hexdigest()
    spec['modules'][0]['observed_identity']=identity(rev)
    result=plan(spec)
    assert result['module_evidence']['io_a']['identity_match']['status']=='matches_supplied_observation'
    assert not result['ready_for_drawing']

@pytest.mark.parametrize('case',['unknown_revision','missing_revision','wrong_vendor','bad_hash','duplicate_address','duplicate_channel','shared_common','safety','extra_field','missing_address_source'])
def test_rejections(spec,case):
    import copy
    m=spec['modules'][0];s=spec['signals'][0]
    if case=='unknown_revision':m['observed_identity']=identity('0x99999999')
    if case=='missing_revision':m['observed_identity']=identity('0x01100000')
    if case=='wrong_vendor':m['observed_identity']={**identity(),'vendor_id':'0x42'}
    if case=='bad_hash':spec['esi']['sha256']='0'*64
    if case=='duplicate_address':
        s['plc_address']={'value':'Y256','source':'fixture'}
        other=copy.deepcopy(s);other['id']='LAMP2';other['target']['channel']=1;spec['signals'].append(other)
    if case=='duplicate_channel':spec['signals'].append({**s,'id':'LAMP2'})
    if case=='shared_common':
        s['potential']='SUPPLY_A';other=copy.deepcopy(s);other['id']='LAMP2';other['target']['channel']=1;other['potential']='SUPPLY_B';spec['signals'].append(other)
    if case=='safety':s['purpose']='emergency_stop'
    if case=='extra_field':s['address']='Y256'
    if case=='missing_address_source':s['plc_address']={'value':'Y256','source':''}
    with pytest.raises(ValueError):plan(spec)

def test_changed_pdo_rejected(spec):
    from pathlib import Path
    p=Path(spec['esi']['path']);raw=xml().replace(b'#x6200',b'#x6300');p.write_bytes(raw)
    with pytest.raises(ValueError,match='PDO differs'):inspect_esi(str(p),hashlib.sha256(raw).hexdigest())

def test_even_complete_mapping_does_not_enable_cad(spec):
    m=spec['modules'][0];m['observed_identity']=identity();m['station']={'position':1,'source':'fixture'}
    s=spec['signals'][0];s.update(original={'signal':'ORIGINAL_OUTPUT','terminal':'X1:1','page':'405'},
        potential='SUPPLY',wire_number='TEST_1',plc_address={'value':'Y256','source':'fixture'},evidence=['fixture'])
    out=plan(spec)
    assert out['mapping_complete'] and not out['ready_for_drawing'] and not out['submitted']
    assert out['signals'][0]['global_plc_address']=='Y256'

def test_dtd_rejected(tmp_path):
    p=tmp_path/'bad.xml';raw=b'<!DOCTYPE x [<!ENTITY x "test">]>'+xml();p.write_bytes(raw)
    with pytest.raises(ValueError,match='DTD'):inspect_esi(str(p),hashlib.sha256(raw).hexdigest())
