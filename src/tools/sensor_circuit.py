"""Executable sensor fixture composed from qualified symbol/connection primitives."""
from copy import deepcopy
from src.tools.delta_mapping import fields
from src.tools.delta_batch import plan as r2_plan
from src.tools.circuit_blocks import cable_pair, wire, signal_pair, device as device_component

def build(spec, preflight):
    cfg=spec['execution'];fields(cfg,['symbol_path','shared_loads'],'sensor execution')
    if type(cfg['shared_loads']) is not bool:raise ValueError('Explicit shared_loads boolean required')
    field_page,io_page=preflight['pages']['logical_pages']
    target=preflight['target_endpoint']
    if target['port'] != 0 or target['channel'] not in (0,1,2):
        raise ValueError('Sensor drawing layout qualified only for Port0 channels 0..2')
    base=r2_plan(dict(schema_version=2,recipe='delta_r2_output_poc',purpose='test_only',symbol_path=cfg['symbol_path'],
        manifest={'schema_version':1,'entries':[deepcopy(spec['manifest']['entries'][1])]}))
    cs=[c for c in base['components'] if c['id'] not in {'lamp','t1','t2','t3'}]
    ws=[w for w in base['connections'] if w['id'].startswith('module_')]
    def comp(ident,role,symbol,x,y,attrs):
        cs.append(dict(id=ident,role=role,symbol=symbol,drawing_page=field_page,x=x,y=y,attributes=attrs))
    cs.append(device_component('sensor','sensor',field_page,350,180,spec['sensor']['tag'],{'DESC1':'SENSOR TEST ONLY','DESC2':'HARDWARE UNVERIFIED'}))
    r2=next(c for c in cs if c['id']=='r2')
    r2['attributes']['DESC3']='SENSOR INPUT TEST '+target['terminal']
    routes=preflight['routes']
    parts,links,markers,refs=cable_pair(routes,field_page,[( 'sensor',pin,r['wire_number'],r['wire_layer']) for pin,r in zip(['X2TERM02','X2TERM03','X8TERM01'],routes)],'THREE_CORE_TEST')
    cs.extend(parts);ws.extend(links)
    input_y=238-3*target['channel']
    parts,signal_refs=signal_pair('TEST_I546',('di_src',field_page,35,160),('di_dst',io_page,50,input_y))
    cs.extend(parts);refs.extend(signal_refs)
    ws.extend([wire('input_to_arrow','di_src','X1TERM01','strip_sensor_signal','X4TERM01','TEST_I546','TEST_SIGNAL'),
               wire('module_input','di_dst','X1TERM01','r2',target['electrical_connection'],'TEST_I546','TEST_SIGNAL')])
    if cfg['shared_loads']:
        cs.append(device_component('button','button',field_page,320,220,f'-{field_page}S_TEST',{'DESC1':'SHARED SUPPLY TEST'}))
        cs.append(device_component('lamp','lamp',field_page,240,220,f'-{field_page}H_TEST',{'DESC1':'SHARED RETURN TEST'}))
        comp('button_boundary','terminal','HT0001',320,202,{'TAGSTRIP':'-XBOUND','TERM01':'BUTTON'})
        comp('lamp_boundary','terminal','HT0001',240,235,{'TAGSTRIP':'-XBOUND','TERM01':'LAMP'})
        ws.extend([wire('button_signal','button','X8TERM02','button_boundary','X2TERM01','TEST_BUTTON','TEST_SIGNAL'),
                   wire('lamp_feed','lamp_boundary','X8TERM01','lamp','X2TERM01','TEST_LAMP','TEST_SIGNAL')])
        for ident,device,pin,target_id,tap,number,layer,sensor_pin in [
            ('shared_supply','button','X2TERM01','field_sensor_supply',[320,240],'TEST24','TEST_24V','X2TERM02'),
            ('shared_return','lamp','X8TERM02','field_sensor_return',[240,200],'TEST0','TEST_0V','X2TERM03')]:
            ws.append({**wire(ident,device,pin,'sensor',sensor_pin,number,layer),'kind':'branch','target_wire':target_id,'tap':tap})
    tags=[c['attributes']['TAG1'].casefold() for c in cs if 'TAG1' in c['attributes']]
    if len(tags)!=len(set(tags)):raise ValueError('Duplicate component identities')
    from src.tools.circuit_blocks import validate_circuit
    validate_circuit(cs,ws,markers)
    return dict(execution_supported=True,status='sensor_test_recipe_planned',components=cs,connections=ws,cable_markers=markers,
        expected_references=refs,component_plan={'components':[{'id':c['id'],'tag':c['attributes']['TAG1']} for c in cs if 'TAG1' in c['attributes']]},
        native_path_acceptance=True,binding={'pending':preflight['mapping']['pending']+['Sensor physical model/output type unverified']},scope='sensor_paths_test_only',shared_loads=cfg['shared_loads'])
