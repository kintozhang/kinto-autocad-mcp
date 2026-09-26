"""Bounded TREBI recipe: native Electrical calls, never model-generated commands."""
import json
import math
import re
import uuid
from pathlib import Path
from src.autocad.trebi_project_pages import plan as page_plan
from src.autocad.trebi_component_tags import plan_tags
from src.autocad.trebi_rules import zone_at, profile
from src.autocad.trebi_native_grid import settings, configure
from src.autocad.trebi_title_mapping import binding, WDT, apply as apply_title

ROOT = Path(__file__).resolve().parents[2]
LIB = Path('C:/Users/Public/Documents/Autodesk/Acade 2026/Libs/iec2')
SYMBOLS = {'primary': ('HCR1', {'X4TERM01','X1TERM02'}),
           'child': ('HCR21', {'X4TERM01','X1TERM02'}),
           'terminal': ('HT0001', {'X4TERM01','X1TERM01'}),
           'source': ('HA1S1', {'X4TERM01'}),
           'destination': ('HA1D3', {'X1TERM01'})}

def plan(spec):
    if not isinstance(spec, dict) or set(spec) != {'schema_version','manifest','components','connections'} or spec['schema_version'] != 1:
        raise ValueError('Expected version 1 manifest, components and connections')
    pages = page_plan(spec['manifest'])
    if not 1 <= pages['effective_drawing_count'] <= 8:
        raise ValueError('Batch supports 1..8 effective prepared drawings')
    names=set()
    for entry in spec['manifest']['entries']:
        if entry['kind']!='drawing' or not entry['include_in_total']: continue
        name=entry.get('drawing_file')
        if not isinstance(name,str) or Path(name).name!=name or Path(name).suffix.lower()!='.dwg' or name.casefold() in names:
            raise ValueError('Unique local DWG filenames required')
        names.add(name.casefold())
    items = spec['components']; links = spec['connections']
    if not isinstance(items,list) or not 1 <= len(items) <= 48 or not isinstance(links,list) or len(links)>48:
        raise ValueError('Bounded component/connection lists required')
    devices=[]; by_id={}; positions=set(); terminals=set(); signals={}
    for c in items:
        if not isinstance(c,dict) or not isinstance(c.get('id'),str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',c['id']) or c['id'] in by_id:
            raise ValueError('Unique simple component id required')
        role=c.get('role'); sheet=c.get('drawing_page')
        if role not in SYMBOLS or sheet not in pages['logical_pages']:
            raise ValueError('Unsupported role or ineffective drawing page')
        allowed={'id','role','drawing_page','x','y','attributes'}
        allowed |= {'family','owner_page','sequence','existing_tag'} if role=='primary' else {'parent_id','existing_tag'} if role=='child' else {'strip','pin'} if role=='terminal' else {'signal_code'}
        if set(c)-allowed: raise ValueError('Unknown component fields')
        for key,low,high in [('x',20,400),('y',50,273)]:
            v=c.get(key)
            if type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high:
                raise ValueError('Component outside usable drawing area')
        position=(sheet,c['x'],c['y'])
        if position in positions: raise ValueError('Coincident component insertion points')
        positions.add(position)
        attrs=c.get('attributes',{})
        allowed_attrs={'DESC1','DESC2','DESC3'} | ({'MFG','CAT'} if role in {'primary','terminal'} else set())
        if not isinstance(attrs,dict) or set(attrs)-allowed_attrs or any(not isinstance(v,str) or len(v)>200 or any(ord(ch)<32 for ch in v) for v in attrs.values()):
            raise ValueError('Unsupported attributes; identities/pins are controlled by recipe')
        if role in {'primary','child'}:
            if role=='primary' and c.get('family')!='K': raise ValueError('Only verified K relay family supported')
            devices.append(c)
        elif role=='terminal':
            if not isinstance(c.get('strip'),str) or not re.fullmatch(r'X[A-Za-z0-9_-]+',c['strip']) or not isinstance(c.get('pin'),str) or not re.fullmatch(r'[A-Za-z0-9_-]+',c['pin']):
                raise ValueError('Explicit terminal strip and pin required')
            endpoint=(c['strip'].casefold(),c['pin'].casefold())
            if endpoint in terminals: raise ValueError('Duplicate terminal strip/pin')
            terminals.add(endpoint)
        else:
            code=c.get('signal_code')
            if not isinstance(code,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',code): raise ValueError('Explicit signal code required')
            pair=signals.setdefault(code,{})
            if role in pair: raise ValueError('Ambiguous source/destination pair')
            pair[role]=c
        by_id[c['id']]=c
    tags=plan_tags(spec['manifest'],devices)
    tagmap={c['id']:c['tag'] for c in tags['components']}
    planned=[]; refs=[]; parents=set()
    for c in items:
        role=c['role']; attrs=dict(c.get('attributes',{}))
        if role=='primary': attrs.update(TAG1=tagmap[c['id']],TERM01='A1',TERM02='A2')
        elif role=='child':
            parent=by_id[c['parent_id']]
            if parent['id'] in parents: raise ValueError('One verified NO child per parent in this batch version')
            parents.add(parent['id']);attrs.update(TAG2=tagmap[c['id']],TERM01='13',TERM02='14')
            refs.extend([{'id':c['id'],'field':'XREF','value':f"{parent['drawing_page']}.{zone_at(parent['x'])}"},
                         {'id':parent['id'],'field':'XREFNO','value':f"{c['drawing_page']}.{zone_at(c['x'])}"}])
        elif role=='terminal': attrs.update(TAGSTRIP=c['strip'],TERM01=c['pin'])
        else: attrs.update(SIGCODE=c['signal_code'])
        planned.append({**c,'symbol':SYMBOLS[role][0],'attributes':attrs})
    for pair in signals.values():
        if set(pair)!={'source','destination'}: raise ValueError('Signal requires exactly one source and destination')
        for role,other in [('source','destination'),('destination','source')]:
            a,b=pair[role],pair[other]
            refs.append({'id':a['id'],'field':'XREF','value':f"{b['drawing_page']}.{zone_at(b['x'])}"})
    used=set(); linkids=set()
    for link in links:
        if not isinstance(link,dict) or set(link)-{'id','from_id','from_connection','to_id','to_connection','wire_number'}:
            raise ValueError('Invalid connection fields')
        if not isinstance(link.get('id'),str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',link['id']) or link['id'] in linkids:
            raise ValueError('Unique connection id required')
        linkids.add(link['id']); endpoints=[]
        for side in ['from','to']:
            c=by_id.get(link.get(side+'_id')); pin=link.get(side+'_connection')
            if c is None or pin not in SYMBOLS[c['role']][1]: raise ValueError('Unverified connection point')
            endpoint=(c['id'],pin)
            if endpoint in used: raise ValueError('Branch/repeated connection requires separate verified workflow')
            used.add(endpoint);endpoints.append(c)
        if endpoints[0]['id']==endpoints[1]['id'] or endpoints[0]['drawing_page']!=endpoints[1]['drawing_page']:
            raise ValueError('Wire endpoints must be distinct and on one drawing')
        if endpoints[0]['y']!=endpoints[1]['y']: raise ValueError('Batch currently accepts horizontal aligned wires only')
        left,right=sorted(endpoints,key=lambda c:c['x'])
        pins={link['from_id']:link['from_connection'],link['to_id']:link['to_connection']}
        if right['x']-left['x']<20 or not pins[left['id']].startswith('X1TERM') or not pins[right['id']].startswith('X4TERM'):
            raise ValueError('Horizontal batch wire requires separated facing connection points')
        if 'wire_number' in link and (not isinstance(link['wire_number'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',link['wire_number'])):
            raise ValueError('Explicit simple wire number required')
    for pair in signals.values():
        wires=[next((w for w in links if c['id'] in (w['from_id'],w['to_id'])),None) for c in pair.values()]
        if any(w is None for w in wires): raise ValueError('Each signal arrow must connect to a wire')
        numbers={w['wire_number'] for w in wires if w.get('wire_number')}
        if len(numbers)!=1: raise ValueError('Signal network needs one consistent explicit wire number')
    return {'success':True,'submitted':False,'pages':pages,'component_plan':tags,
            'components':planned,'connections':links,'expected_references':refs,
            'scope':'prepared_blank_trebi_pages; verified_iec2_subset; no_catalog_selection'}


def execute(project_path,spec,drawing_path):
    from src.autocad.connection import get_connection
    from src.autocad.com_runtime import read_call,wait_for_document
    from src.autocad.utils import get_block_attributes
    from src.autocad.lisp_bridge import evaluate,literal
    from src.tools.native_project import guard,export_report,update_signals
    from src.tools.native_cross_references import update
    from src.tools.native_electrical import insert_symbol,connect_terminals,set_number,inspect_wire
    # No CAD mutations (including activation) before structural/file preflight.
    try:
        recipe=plan(spec); project=Path(project_path); original=Path(drawing_path)
        if not project.is_absolute() or project.suffix.lower()!='.wdp' or not original.is_absolute(): raise ValueError('Absolute project/DWG paths required')
        bound,_=binding(spec['manifest'],project,original)
        if project.with_suffix('.wdt').read_text(encoding='utf8')!=WDT.read_text(encoding='utf8'): raise ValueError('Unverified WDT mapping')
        lines=project.read_text(encoding='utf-8-sig').splitlines()
        if [v for v in lines if v.startswith('*[20]')]!=['*[20]'+str(recipe['pages']['effective_drawing_count'])]: raise ValueError('LINE20 differs from effective page count')
        if any(not (LIB/(c['symbol']+'.dwg')).is_file() for c in recipe['components']): raise ValueError('Verified IEC2 symbol library missing')
        conn=get_connection(); app=conn.get_application(); hwnd=read_call(lambda:int(app.HWND))
        if Path(read_call(lambda:app.ActiveDocument.FullName)).resolve()!=original.resolve(): raise ValueError('Wrong active target')
        state=guard(conn,str(project))
        if [str(Path(p).resolve()).casefold() for p in state['drawings']]!=list(bound): raise ValueError('Project membership/order differs from manifest')
        docs={str(Path(d.FullName).resolve()).casefold():d for d in app.Documents if d.FullName}
        for filename,row in bound.items():
            doc=docs.get(filename)
            if doc is None or not read_call(lambda:bool(doc.Saved)): raise ValueError('Every target page must already be open and saved')
            objects=list(doc.ModelSpace)
            if len(objects)!=2 or any(e.ObjectName!='AcDbBlockReference' for e in objects) or {e.Name for e in objects}!={'WD_M',profile()['block_name']}:
                raise ValueError('Batch requires blank WD_M + TREBI frame; never replay into populated drawings')
            attrs={e.Name:get_block_attributes(e) for e in objects}
            if not set(settings(row['logical_page']))<=set(attrs['WD_M']) or not set(row['title_fields'])<=set(attrs[profile()['block_name']]): raise ValueError('Missing native/title attributes')
    except Exception as exc:
        return {'success':False,'status':'preflight_rejected','submitted':False,'error':str(exc)}
    folder=ROOT/'work/batches'/uuid.uuid4().hex;folder.mkdir(parents=True)
    receipt=folder/'report.json'
    report={'success':False,'status':'running','submitted':True,'project':str(project),'drawings':state['drawings'],
            'manifest':spec['manifest'],'component_plan':recipe['component_plan'],'steps':[],
            'entities':{},'wires':{},'settings':{},'titles':{},'references':{},'reports':{},'receipt':str(receipt)}
    def persist():
        temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(report,ensure_ascii=True,indent=2),encoding='utf8');temp.replace(receipt)
    def step(name,call):
        item={'step':name,'status':'entered'};report['steps'].append(item);persist()
        value=call();item['result']=value
        if isinstance(value,dict) and value.get('success') is False:
            item['status']='failed';persist();raise RuntimeError(name+': '+str(value))
        item['status']='completed';persist();return value
    def activate(path):
        if read_call(lambda:int(app.HWND))!=hwnd: raise RuntimeError('AutoCAD instance changed')
        docs[str(Path(path).resolve()).casefold()].Activate()
        doc=wait_for_document(app,path)
        conn._bound_document=str(Path(path).resolve());conn._bound_hwnd=hwnd
        evaluate(conn,'(progn (c:wd_makeproj_current '+literal(project.as_posix())+') T)')
        if guard(conn,str(project))!=state: raise RuntimeError('Project changed')
        return doc
    by_page={row['logical_page']:filename for filename,row in bound.items()}
    def save_active():
        doc=conn.get_active_document(); read_call(lambda:doc.Save)()
        wait_for_document(app,doc.FullName)
        if not read_call(lambda:bool(doc.Saved)): raise RuntimeError('Save not confirmed')
        return {'success':True}
    try:
        for sheet,path in by_page.items():
            step('activate:'+sheet,lambda:activate(path) and None)
            report['settings'][sheet]=step('grid:'+sheet,lambda:configure(conn,path,sheet))
            report['titles'][sheet]=step('title:'+sheet,lambda:apply_title(conn,project,spec['manifest'],path))
            step('save:'+sheet,save_active)
        # Parents before children, irrespective of manifest drawing order.
        for c in sorted(recipe['components'],key=lambda c:c['role']!='primary'):
            path=by_page[c['drawing_page']];step('activate:'+c['id'],lambda:activate(path) and None)
            result=step('insert:'+c['id'],lambda:insert_symbol(str(LIB/(c['symbol']+'.dwg')),c['x'],c['y'],attributes=c['attributes']))
            report['entities'][c['id']]={**result,'drawing':path};persist()
        for link in recipe['connections']:
            a=report['entities'][link['from_id']];b=report['entities'][link['to_id']]
            step('activate:'+link['id'],lambda:activate(a['drawing']) and None)
            wire=step('wire:'+link['id'],lambda:connect_terminals(a['handle'],link['from_connection'],b['handle'],link['to_connection']))
            report['wires'][link['id']]=wire;persist()
            if link.get('wire_number'): step('number:'+link['id'],lambda:set_number(wire['wire_handles'][0],link['wire_number']))
        for sheet,path in by_page.items():
            step('activate:'+sheet,lambda:activate(path) and None);step('save:'+sheet,save_active)
        if any(c['role']=='source' for c in recipe['components']):
            for sheet,path in by_page.items():
                if not any(c['drawing_page']==sheet and c['role'] in {'source','destination'} for c in recipe['components']): continue
                step('activate:'+sheet,lambda:activate(path) and None)
                step('signals:'+sheet,lambda:update_signals(str(project)));step('save:'+sheet,save_active)
        if any(c['role']=='child' for c in recipe['components']): step('parent_child_references',lambda:update(str(project)))
        for sheet,path in by_page.items():
            step('activate:'+sheet,lambda:activate(path) and None)
            for c in recipe['components']:
                if c['drawing_page']!=sheet: continue
                attrs=get_block_attributes(conn.get_active_document().HandleToObject(report['entities'][c['id']]['handle']))
                if any(attrs.get(k)!=v for k,v in c['attributes'].items()): raise RuntimeError('Final component attribute mismatch: '+c['id'])
                report['references'][c['id']]=attrs
            for ref in recipe['expected_references']:
                if ref['id'] in report['references'] and report['references'][ref['id']].get(ref['field'])!=ref['value']: raise RuntimeError('Exact reference mismatch: '+str(ref))
            for link in recipe['connections']:
                if report['entities'][link['from_id']]['drawing']!=path: continue
                result=step('read_wire:'+link['id'],lambda:inspect_wire(report['wires'][link['id']]['wire_handles'][0]))
                # For an unnumbered destination use its source pair's assigned number.
                number=link.get('wire_number')
                if number is None:
                    ends=[c for c in recipe['components'] if c['id'] in (link['from_id'],link['to_id']) and c['role'] in {'source','destination'}]
                    if ends:
                        partners={c['id'] for c in recipe['components'] if c.get('signal_code')==ends[0]['signal_code']}
                        number=next((w['wire_number'] for w in recipe['connections'] if w.get('wire_number') and partners.intersection({w['from_id'],w['to_id']})),None)
                if number is not None and result['wire_number']!=number: raise RuntimeError('Final wire number mismatch')
            step('save:'+sheet,save_active)
        for kind in ['bom','from_to','terminal_plan','terminal_numbers']:
            report['reports'][kind]=step('report:'+kind,lambda:export_report(str(project),kind,str(folder/(kind+'.csv'))))
        step('restore_original',lambda:activate(original) and None)
        report.update(success=True,status='native_readback_verified',save_reopen='pending_independent_verification')
    except Exception as exc:
        report.update(status='partial_or_unknown',error=str(exc),automatic_retry=False)
    finally: persist()
    return report
