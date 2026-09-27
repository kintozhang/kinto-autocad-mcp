"""Read-only, source-referenced R2 family channel planning. No CAD or PLC writes."""
import json
import re
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[2]/'profiles/delta-r2-ec0902.json'


def plan(spec):
    if isinstance(spec, dict) and type(spec.get("schema_version")) is int and spec["schema_version"] == 3:
        from src.tools.delta_module_inventory import plan as inventory_plan
        return inventory_plan(spec)
    if isinstance(spec, dict) and type(spec.get("schema_version")) is int and spec["schema_version"] == 2:
        from src.tools.delta_mapping import plan_v2
        return plan_v2(spec)
    if not isinstance(spec,dict) or set(spec)!={'schema_version','modules','signals'} or type(spec['schema_version']) is not int or spec['schema_version']!=1:
        raise ValueError('Expected version 1 modules/signals specification')
    cfg=json.loads(PROFILE.read_text(encoding='utf8'));modules={};used=set();commons={};signals=[];ids=set()
    if not isinstance(spec['modules'],list) or not 1<=len(spec['modules'])<=16 or not isinstance(spec['signals'],list) or not 1<=len(spec['signals'])<=1024:
        raise ValueError('Bounded nonempty module and signal lists required')
    def identifier(value):
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',value):raise ValueError('Simple nonempty identifier required')
        return value
    for mod in spec['modules']:
        if not isinstance(mod,dict) or set(mod)!={'id','model','input_mode'}:raise ValueError('Module fields: id, model, input_mode')
        key=identifier(mod['id'])
        if key.casefold() in modules:raise ValueError('Duplicate module instance')
        if mod['model'] not in {cfg['family'],cfg['family']+'D0'}:raise ValueError('Unsupported model; do not substitute another R2 variant')
        if mod['input_mode'] not in {'PNP','NPN'}:raise ValueError('One shared PNP/NPN input mode per module required')
        modules[key.casefold()]=mod
    for signal in spec['signals']:
        if not isinstance(signal,dict) or set(signal)!={'id','module_id','port','channel','direction','purpose','potential','source_signal'}:
            raise ValueError('Exact signal fields required; PLC global addresses cannot be inferred')
        key=identifier(signal['id'])
        if key.casefold() in ids:raise ValueError('Duplicate signal id')
        ids.add(key.casefold());module_key=identifier(signal['module_id']).casefold();mod=modules.get(module_key)
        if mod is None:raise ValueError('Unknown module instance')
        port=signal['port'];channel=signal['channel']
        if type(port) is not int or not 0<=port<=3 or type(channel) is not int or not 0<=channel<=15:
            raise ValueError('Physical port 0..3 and decimal channel 0..15 required')
        p=cfg['ports'][port]
        if signal['direction']!=p['direction']:raise ValueError('Direction disagrees with physical port')
        if signal['purpose']!='ordinary_control':raise ValueError('This planner does not map safety functions')
        for field in ['potential','source_signal']:
            value=signal[field]
            if not isinstance(value,str) or not value.strip() or len(value)>200 or any(ord(c)<32 for c in value):raise ValueError('Explicit literal potential and source signal required')
        endpoint=(module_key,port,channel)
        if endpoint in used:raise ValueError('Duplicate physical channel assignment')
        used.add(endpoint)
        terminal=p['prefix']+f'{channel:02d}'
        if p['direction']=='input':
            common=p['input_common'];common_connection='IO_0V' if mod['input_mode']=='PNP' else 'IO_24V'
            electrical_type=mod['input_mode']+'_input'
        else:
            common=p['connector']+':C'+str(p['first_common']+channel//4);common_connection=signal['potential'];electrical_type=p['output_type']
            group=(module_key,common)
            if group in commons and commons[group]!=signal['potential']:raise ValueError('One relay common group cannot use multiple potentials')
            commons[group]=signal['potential']
        signals.append({'id':key,'source_signal':signal['source_signal'],'potential':signal['potential'],
            'module_id':mod['id'],'requested_model':mod['model'],'documented_family':cfg['family'],
            'port':port,'connector':p['connector'],'channel':channel,'terminal':terminal,
            'endpoint':f"{mod['id']}/Port{port}/{terminal}",'electrical_type':electrical_type,
            'common_terminal':common,'common_connection_draft':common_connection,
            'object_index':p['object_index'],'subindex':p['first_subindex']+channel//8,
            'derived_bit_candidate':channel%8,'global_plc_address':None,'process_image_offset':None,
            'port_source_pdf_page':cfg['source']['pdf_pages']['port'+str(port)],'object_source_pdf_page':113})
    return {'success':True,'status':'documented_hardware_draft','cad_contacted':False,'submitted':False,
        'ready_for_drawing':False,'source':cfg['source'],'signals':signals,'modules':list(modules.values()),
        'limitations':cfg['limitations'],'pending':['Match ordering suffix/ESI/revision to physical modules','Record actual NC50 mapping and test channel bits','Accept native Electrical remote I/O symbol and channel wiring before drawing']}
