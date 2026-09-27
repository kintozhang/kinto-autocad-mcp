"""Bounded ordinary-control path recipe; unknown field bindings never grant release."""
from copy import deepcopy
from pathlib import Path
import re
from src.tools.delta_mapping import plan_v2, fields, literal
from src.tools.delta_batch import plan as output_plan
from src.autocad.trebi_project_pages import plan as page_plan
from src.autocad.trebi_rules import zone_at

ROLES=('button_supply','button_return','lamp_feed','lamp_return')

def validate_routes(routes):
    if not isinstance(routes,list) or len(routes)!=4:
        raise ValueError('Exactly four supply/input/output/return paths required')
    by_id={};cores=set();pins=set();terminals=set();pairs=set();cables=set()
    for r in routes:
        fields(r,['id','original','strip','terminal','cable','core','socket','plug','socket_pin','plug_pin','device','device_terminal','source'],'route')
        for k,v in r.items():literal(v,'route '+k)
        if r['id'] not in ROLES or r['id'] in by_id:raise ValueError('Missing or duplicate path role')
        for k in ('strip','terminal','cable','core','socket','plug','socket_pin','plug_pin','device','device_terminal'):
            if not re.fullmatch(r'[-A-Za-z0-9_]{1,32}',r[k]):raise ValueError('Simple literal route identity required')
        if r['socket'].casefold()==r['plug'].casefold():raise ValueError('Socket and plug must be distinct physical halves')
        if r['socket_pin']!=r['plug_pin']:raise ValueError('Mating pin mismatch')
        for seen,key,label in [(cores,(r['cable'].casefold(),r['core'].casefold()),'cable core'),(pins,(r['socket'].casefold(),r['socket_pin'].casefold()),'connector pin'),(terminals,(r['strip'].casefold(),r['terminal'].casefold()),'strip terminal')]:
            if key in seen:raise ValueError('Duplicate '+label)
            seen.add(key)
        pairs.add((r['socket'],r['plug']));cables.add(r['cable']);by_id[r['id']]=r
    if set(by_id)!=set(ROLES) or len(pairs)!=1 or len(cables)!=1:raise ValueError('One complete cable and mating pair required')
    for a,b,ta,tb in [('button_supply','button_return','13','14'),('lamp_feed','lamp_return','1','2')]:
        if by_id[a]['device']!=by_id[b]['device'] or (by_id[a]['device_terminal'],by_id[b]['device_terminal'])!=(ta,tb):raise ValueError('Missing or wrong device terminals')
    identities=[routes[0]['socket'],routes[0]['plug'],routes[0]['cable'],routes[0]['strip']]
    devices={r['device'].casefold() for r in routes}
    if len({s.casefold() for s in identities})!=4 or devices.intersection(s.casefold() for s in identities):raise ValueError('Physical device/cable/connector identities collide')
    return [deepcopy(by_id[k]) for k in ROLES]

def validate_bindings(mapping, binding):
    fields(binding,['controller','protocol','ss_potential','output_common_potential','source','observations'],'binding')
    if binding['controller']!='NC50E-FE' or binding['protocol']!='EtherCAT':raise ValueError('NC50 controller and EtherCAT remote IO required')
    if binding['ss_potential']!='TEST_0V' or binding['output_common_potential']!='TEST_24V':raise ValueError('PNP S/S must use 0V; relay C0 must use selected 24V supply')
    literal(binding['source'],'common wiring source')
    fields(binding['observations'],['BUTTON','LAMP'],'PDO observations')
    pending=list(mapping['pending']);checks=[]
    for s in mapping['signals']:
        obs=binding['observations'][s['id']]
        if obs is None:
            pending.append(s['id']+': NC50 PDO/bit binding observation missing');continue
        fields(obs,['object_index','subindex','bit','plc_address','source'],'PDO observation')
        literal(obs['source'],'PDO source');literal(obs['plc_address'],'observed NC50 address')
        from src.autocad.delta_esi import integer
        if integer(obs['object_index'])!=integer(s['object_index']) or type(obs['subindex']) is not int or obs['subindex']!=s['subindex'] or type(obs['bit']) is not int or obs['bit']!=s['derived_bit_candidate']:
            raise ValueError('PDO object/subindex/bit disagrees with physical channel: '+s['id'])
        if s['global_plc_address'] is None or obs['plc_address']!=s['global_plc_address']:raise ValueError('NC50 address differs from explicit signal mapping')
        checks.append({'signal':s['id'],'status':'matches_supplied_observation','hardware_contacted':False})
    return {'checks':checks,'pending':pending,'production_ready':False,'formal_export_allowed':False}

def plan(spec):
    fields(spec,['schema_version','recipe','purpose','manifest','symbol_path','mapping','routes','binding'] + (['eio_assumptions'] if 'eio_assumptions' in spec else []),'full-path recipe')
    if type(spec['schema_version']) is not int or spec['schema_version']!=4 or spec['recipe']!='remote_io_button_lamp_paths' or spec['purpose']!='test_only':raise ValueError('Version 4 test_only full paths required')
    pages=page_plan(spec['manifest']);entries=spec['manifest']['entries']
    if len(entries)!=2 or pages['logical_pages']!=['102','300'] or pages['effective_drawing_count']!=2:raise ValueError('Prepared effective pages 102,300 required')
    names=[e.get('drawing_file') for e in entries]
    if any(not isinstance(n,str) or Path(n).name!=n or Path(n).suffix.lower()!='.dwg' for n in names) or len({n.casefold() for n in names})!=2:raise ValueError('Unique local DWG names required')
    routes=validate_routes(spec['routes']);mapping=plan_v2(spec['mapping']);modules=spec['mapping']['modules']
    ss={s['id']:s for s in mapping['signals']}
    if len(modules)!=1 or modules[0]['input_mode']!='PNP' or set(ss)!={'BUTTON','LAMP'}:raise ValueError('One PNP remote IO and BUTTON/LAMP required')
    for key,port,number,route in [('BUTTON',0,'TEST_DI',routes[1]),('LAMP',2,'TEST_DO',routes[2])]:
        s=ss[key]
        if (s['port'],s['channel'],s['wire_number'],s['potential'])!=(port,0,number,'TEST_24V'):raise ValueError('Unverified fixture channel/potential/number')
        if s['original']['signal']!=route['original']:raise ValueError('Original signal differs from route reference')
    binding=validate_bindings(mapping,spec['binding'])
    base=output_plan({'schema_version':2,'recipe':'delta_r2_output_poc','purpose':'test_only','symbol_path':spec['symbol_path'],'manifest':{'schema_version':1,'entries':[deepcopy(entries[1])]}})
    cs=[c for c in base['components'] if c['id'] not in {'lamp','t2','t3'}]
    next(c for c in cs if c['id']=='r2')['attributes']['DESC3']='DI DO FULL PATH TEST'
    ws=[w for w in base['connections'] if w['id'] not in {'output','lamp_feed','lamp_return'}];refs=[];markers=[]
    def comp(id,role,symbol,page,x,y,attrs,**extra):
        cs.append(dict(id=id,role=role,symbol=symbol,drawing_page=page,x=x,y=y,attributes=attrs,**extra))
    def wire(id,a,ap,b,bp,num,layer):ws.append(dict(id=id,from_id=a,from_connection=ap,to_id=b,to_connection=bp,wire_number=num,wire_layer=layer,exact_network=True))
    comp('button','button_test','VPB11','102',300,220,{'TAG1':routes[0]['device'],'TERM01':'13','TERM02':'14','MFG':'KINTO_TEST','CAT':'BUTTON_NO_TEST','DESC1':'INPUT TEST ONLY'})
    comp('lamp','delta_lamp_test','VLT1G','102',300,140,{'TAG1':routes[2]['device'],'TERM01':'1','TERM02':'2','MFG':'KINTO_TEST','CAT':'LAMP_24V_TEST','DESC1':'STEADY OUTPUT TEST'})
    pins=[r['socket_pin'] for r in routes]
    for id,side,x,tag in [('socket','socket',170,routes[0]['socket']),('plug','plug',190,routes[0]['plug'])]:
        comp(id,'connector_half',None,'102',x,240,{'TAG1':tag,'MFG':'KINTO_TEST','CAT':'CONNECTOR_'+side.upper()+'_TEST','DESC1':'MATES '+(routes[0]['plug'] if side=='socket' else routes[0]['socket'])},side=side,pins=pins)
    for i,(r,num,layer,dev,pin) in enumerate(zip(routes,['TEST24','TEST_DI','TEST_DO','TEST0'],['TEST_24V','TEST_SIGNAL','TEST_SIGNAL','TEST_0V'],['button','button','lamp','lamp'],['X2TERM01','X8TERM02','X2TERM01','X8TERM02'])):
        y=240-40*i;tid='strip_'+r['id'];wid='cable_'+r['id']
        comp(tid,'terminal','HT0001','102',75,y,{'TAGSTRIP':r['strip'],'TERM01':r['terminal']})
        wire(wid,tid,'X1TERM01','socket',f'X4TERM{i+1:02d}J',num,layer)
        wire('field_'+r['id'],'plug',f'X1TERM{i+1:02d}P',dev,pin,num,layer)
        markers.append(dict(id='core_'+r['id'],role='cable_parent' if i==0 else 'cable_child',symbol='HW01' if i==0 else 'HW02',drawing_page='102',x=115,y=y,attributes={('TAG1' if i==0 else 'TAG2'):r['cable'],'RATING1':r['core'],**({'MFG':'KINTO_TEST','CAT':'FOUR_CORE_TEST'} if i==0 else {})},wire_id=wid))
    for code,src,dst,src_symbol in [('TEST_DI',('di_src','102',35,200),('di_dst','300',50,238),'HA1S3'),('TEST_DO',('do_src','300',250,238),('do_dst','102',35,160),'HA1S1')]:
        for role,item,other,symbol in [('source',src,dst,src_symbol),('destination',dst,src,'HA1D3')]:
            id,page,x,y=item;comp(id,role,symbol,page,x,y,{'SIGCODE':code},signal_code=code)
            refs.append({'id':id,'field':'XREF','value':f'{other[1]}.{zone_at(other[2])}'})
    wire('input_to_arrow','di_src','X1TERM01','strip_button_return','X4TERM01','TEST_DI','TEST_SIGNAL')
    wire('output_from_arrow','do_dst','X1TERM01','strip_lamp_feed','X4TERM01','TEST_DO','TEST_SIGNAL')
    wire('module_input','di_dst','X1TERM01','r2','X4TERM01','TEST_DI','TEST_SIGNAL')
    wire('module_output','r2','X1TERM33','do_src','X4TERM01','TEST_DO','TEST_SIGNAL')
    cable_zone='102.'+str(zone_at(115))
    for i,marker in enumerate(markers):
        refs.append({'id':marker['id'],'field':'XREF','value':','.join([cable_zone]*3) if i==0 else cable_zone})
    nc50 = None
    if 'eio_assumptions' in spec:
        from src.tools.nc50_test_mapping import plan as nc50_plan
        nc50 = nc50_plan({'schema_version':4,'purpose':'test_only','mapping':spec['mapping'],'eio_assumptions':spec['eio_assumptions']})
        if not nc50['test_plan_valid']:raise ValueError('NC50 test candidates conflict with explicit addresses')
        candidates={c['signal_id']:c['nc50_address_candidate'] for c in nc50['candidates']}
        for component_id,signal in [('button','BUTTON'),('lamp','LAMP')]:
            next(c for c in cs if c['id']==component_id)['attributes']['DESC2']='TEST NC50 '+candidates[signal]
        r2=next(c for c in cs if c['id']=='r2')['attributes']
        r2['DESC2']='TEST CANDIDATES - NOT VERIFIED'
        r2['DESC3']='NC50 '+candidates['BUTTON']+' / '+candidates['LAMP']
    tags={}
    for component in cs:
        tag=component['attributes'].get('TAG1')
        if tag:tags.setdefault(tag.casefold(),set()).add(component['id'])
    if any(len(ids)>1 and ids!={'button','lamp'} for ids in tags.values()):raise ValueError('Duplicate physical device tag in recipe')
    # Native netlist ends at terminal sides; the route model records terminal continuity.
    for w in ws:w.pop('exact_network',None)
    return dict(success=True,submitted=False,pages=pages,components=cs,connections=ws,cable_markers=markers,expected_references=refs,
        component_plan={'components':[{'id':c['id'],'tag':c['attributes']['TAG1']} for c in cs if 'TAG1' in c['attributes']]},
        routes=routes,mapping=mapping,binding=binding,nc50_test_plan=nc50,production_ready=False,formal_export_allowed=False,
        scope='remote_io_button_lamp_paths_test_only',limitations=['Physical mating is a declared pair, not a jumper wire','Supply boundary terminals only; other original branches excluded','Unknown NC50/hardware bindings block formal output','Not a safety or PLC functional-equivalence acceptance'])
