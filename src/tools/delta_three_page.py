"""Bounded three-page DI/DO fixture; localization evidence never grants production approval."""
from copy import deepcopy
from src.tools.delta_batch import plan as output_plan
from src.tools.delta_mapping import plan_v2
from src.autocad.trebi_project_pages import plan as page_plan
from src.autocad.trebi_rules import zone_at

def plan(spec):
    required={'schema_version','recipe','purpose','manifest','symbol_path','mapping'}
    if not isinstance(spec,dict) or set(spec)!=required or type(spec['schema_version']) is not int or spec['schema_version']!=3 or spec['recipe']!='delta_di_do_three_page' or spec['purpose']!='test_only':
        raise ValueError('Only version 3 delta_di_do_three_page test_only recipe supported')
    pages=page_plan(spec['manifest'])
    entries=spec['manifest']['entries']
    if len(entries)!=3 or pages['logical_pages']!=['102','300','405'] or pages['effective_drawing_count']!=3:
        raise ValueError('Fixture requires ordered effective pages 102, 300, 405')
    from pathlib import Path
    names=[e.get('drawing_file') for e in entries]
    if any(not isinstance(n,str) or Path(n).name!=n or Path(n).suffix.lower()!='.dwg' for n in names) or len({n.casefold() for n in names})!=3:
        raise ValueError('Unique local DWG filenames required')
    mapping=plan_v2(spec['mapping'])
    modules=spec['mapping']['modules']; signals={s['id']:s for s in mapping['signals']}
    if len(modules)!=1 or modules[0]['input_mode']!='PNP' or set(signals)!={'BUTTON','LAMP'}:
        raise ValueError('One PNP module and BUTTON/LAMP signals required')
    for key,port,number in [('BUTTON',0,'TEST_DI'),('LAMP',2,'TEST_DO')]:
        s=signals[key]
        if s['port']!=port or s['channel']!=0 or s['wire_number']!=number or s['potential']!='TEST_24V':
            raise ValueError('Fixture binding differs: '+key)
    single={'schema_version':2,'recipe':'delta_r2_output_poc','purpose':'test_only','symbol_path':spec['symbol_path'],
            'manifest':{'schema_version':1,'entries':[deepcopy(entries[1])]}}
    base=output_plan(single)
    cs=[c for c in base['components'] if c['id'] not in {'lamp','t2','t3'}]
    next(c for c in cs if c['id']=='r2')['attributes']['DESC3']='SYNTHETIC DI DO TEST'
    ws=[w for w in base['connections'] if w['id'] not in {'output','lamp_feed','lamp_return'}]
    def component(id,role,symbol,page,x,y,attrs):
        cs.append(dict(id=id,role=role,symbol=symbol,drawing_page=page,x=x,y=y,attributes=attrs))
    component('button','button_test','HPB11','102',100,200,{'TAG1':'-102S1','TERM01':'13','TERM02':'14','MFG':'KINTO_TEST','CAT':'BUTTON_NO_TEST','DESC1':'TEST INPUT - NOT SAFETY'})
    component('lamp','delta_lamp_test','HLT1G','405',150,200,{'TAG1':'-405H1','TERM01':'1','TERM02':'2','MFG':'KINTO_TEST','CAT':'LAMP_24V_TEST','DESC1':'STEADY OUTPUT TEST'})
    component('input_supply','terminal','HT0001','102',50,200,{'TAGSTRIP':'-XTEST','TERM01':'8'})
    component('output_return','terminal','HT0001','405',220,200,{'TAGSTRIP':'-XTEST','TERM01':'9'})
    refs=[]
    for code,src,dst in [('TEST_DI',('di_src','102',200,200),('di_dst','300',50,238)),('TEST_DO',('do_src','300',250,238),('do_dst','405',50,200))]:
        for role,item,other,symbol in [('source',src,dst,'HA1S1'),('destination',dst,src,'HA1D3')]:
            id,page,x,y=item
            component(id,role,symbol,page,x,y,{'SIGCODE':code})
            refs.append({'id':id,'field':'XREF','value':f'{other[1]}.{zone_at(other[2])}'})
    def wire(id,a,ap,b,bp,num,layer):
        ws.append(dict(id=id,from_id=a,from_connection=ap,to_id=b,to_connection=bp,wire_number=num,wire_layer=layer))
    wire('button_supply','input_supply','X1TERM01','button','X4TERM01','TEST24','TEST_24V')
    wire('button_signal','button','X1TERM02','di_src','X4TERM01','TEST_DI','TEST_SIGNAL')
    wire('module_input','di_dst','X1TERM01','r2','X4TERM01','TEST_DI','TEST_SIGNAL')
    wire('module_output','r2','X1TERM33','do_src','X4TERM01','TEST_DO','TEST_SIGNAL')
    wire('lamp_signal','do_dst','X1TERM01','lamp','X4TERM01','TEST_DO','TEST_SIGNAL')
    wire('lamp_return','lamp','X1TERM02','output_return','X4TERM01','TEST0','TEST_0V')
    return dict(success=True,submitted=False,pages=pages,components=cs,connections=ws,expected_references=refs,
        component_plan={'components':[{'id':c['id'],'tag':c['attributes']['TAG1']} for c in cs if 'TAG1' in c['attributes']]},
        mapping=mapping,production_ready=False,scope='delta_di_do_three_page_test_only',
        limitations=['Supply boundary terminals; no physical supply joining implied','Synthetic button/lamp; not O518 blink circuit','NC50/hardware acceptance remains independent'])
