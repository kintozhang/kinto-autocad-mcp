"""Reusable, bounded native Electrical circuit fragments (no CAD calls)."""
from src.autocad.trebi_rules import zone_at

def cable_pair(routes, page, endpoints, cable_catalog):
    """Stable 40mm connector pitch; every route has one native cable marker."""
    components=[]; wires=[]; markers=[]; refs=[]
    for ident, side, x in [('socket','socket',170),('plug','plug',190)]:
        other='plug' if side=='socket' else 'socket'
        components.append(dict(id=ident,role='connector_half',symbol=None,drawing_page=page,x=x,y=240,
            attributes={'TAG1':routes[0][side],'MFG':'KINTO_TEST','CAT':'CONNECTOR_'+side.upper()+'_TEST','DESC1':'MATES '+routes[0][other]},
            side=side,pins=[r['socket_pin'] for r in routes]))
    for i,(r,(device,pin,number,layer)) in enumerate(zip(routes,endpoints,strict=True)):
        y=240-40*i;tid='strip_'+r['id'];wid='cable_'+r['id']
        components.append(dict(id=tid,role='terminal',symbol='HT0001',drawing_page=page,x=75,y=y,attributes={'TAGSTRIP':r['strip'],'TERM01':r['terminal']}))
        wires.extend([wire(wid,tid,'X1TERM01','socket',f'X4TERM{i+1:02d}J',number,layer),
            wire('field_'+r['id'],'plug',f'X1TERM{i+1:02d}P',device,pin,number,layer)])
        markers.append(dict(id='core_'+r['id'],role='cable_parent' if i==0 else 'cable_child',symbol='HW01' if i==0 else 'HW02',drawing_page=page,x=115,y=y,
            attributes={('TAG1' if i==0 else 'TAG2'):r['cable'],'RATING1':r['core'],**({'MFG':'KINTO_TEST','CAT':cable_catalog} if i==0 else {})},wire_id=wid))
    zone=page+'.'+str(zone_at(115))
    for i,marker in enumerate(markers):refs.append({'id':marker['id'],'field':'XREF','value':','.join([zone]*(len(routes)-1)) if i==0 else zone})
    return components,wires,markers,refs

def wire(ident,a,ap,b,bp,number,layer):
    return dict(id=ident,from_id=a,from_connection=ap,to_id=b,to_connection=bp,wire_number=number,wire_layer=layer)

def signal_pair(code, source, destination, source_symbol='HA1S3'):
    components=[];refs=[]
    for role,item,other,symbol in [('source',source,destination,source_symbol),('destination',destination,source,'HA1D3')]:
        ident,page,x,y=item
        components.append(dict(id=ident,role=role,symbol=symbol,drawing_page=page,x=x,y=y,attributes={'SIGCODE':code},signal_code=code))
        refs.append({'id':ident,'field':'XREF','value':f'{other[1]}.{zone_at(other[2])}'})
    return components,refs

def validate_circuit(components, connections, markers, shared_tag_pairs=()):
    """Check assembled fragments before any backup, activation or CAD write."""
    import math
    ids={};tags={};terminals=set();wire_ids={}
    allowed_duplicates=[set(pair) for pair in shared_tag_pairs]
    for c in [*components,*markers]:
        if c['id'] in ids:raise ValueError('Duplicate circuit component id')
        ids[c['id']]=c
        for key,low,high in [('x',20,400),('y',50,273)]:
            value=c[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Circuit component outside usable frame')
        attrs=c['attributes']
        if attrs.get('TAG1'):tags.setdefault(attrs['TAG1'].casefold(),set()).add(c['id'])
        if attrs.get('TAGSTRIP'):
            terminal=(attrs['TAGSTRIP'].casefold(),attrs['TERM01'].casefold())
            if terminal in terminals:raise ValueError('Duplicate physical terminal')
            terminals.add(terminal)
    if any(len(group)>1 and group not in allowed_duplicates for group in tags.values()):raise ValueError('Duplicate physical circuit tag')
    for w in connections:
        if w['id'] in wire_ids:raise ValueError('Duplicate circuit wire id')
        a,b=(ids[w[side+'_id']] for side in ('from','to'))
        if a['id']==b['id'] or a['drawing_page']!=b['drawing_page']:raise ValueError('Wire cannot cross drawing or connect a device to itself')
        if w.get('kind') not in (None,'branch'):raise ValueError('Unsupported circuit connection kind')
        if w.get('kind')=='branch':
            target=wire_ids.get(w['target_wire'])
            if target is None or target.get('kind')=='branch':raise ValueError('Branch needs an earlier base wire')
            target_pins={(target[s+'_id'],target[s+'_connection']) for s in ('from','to')}
            if (w['to_id'],w['to_connection']) not in target_pins:raise ValueError('Branch endpoint must belong to target wire')
            if any(w[k]!=target[k] for k in ('wire_number','wire_layer')):raise ValueError('Branch cannot change target potential or wire number')
            if len(w['tap'])!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in w['tap']):raise ValueError('Finite branch coordinates required')
        wire_ids[w['id']]=w

def select_branch_segment(snapshots, tap):
    """Choose from actual wire geometry; never assume the autorouter's path."""
    import json
    from src.tools.native_branch import point_on_segment
    hits=[s['wire_handle'] for s in snapshots if s.get('success') and point_on_segment([*tap,0],s['start'],s['end'])]
    if len(hits)!=1:
        geometry=[{k:s.get(k) for k in ('wire_handle','success','start','end')} for s in snapshots]
        raise ValueError('Branch requires one actual segment: '+json.dumps({'tap':tap,'segments':geometry}))
    return hits[0]

DEVICE_TEMPLATES = {
    'button': ('button_test','VPB11',{'TERM01':'13','TERM02':'14','MFG':'KINTO_TEST','CAT':'BUTTON_NO_TEST'}),
    'lamp': ('delta_lamp_test','VLT1G',{'TERM01':'1','TERM02':'2','MFG':'KINTO_TEST','CAT':'LAMP_24V_TEST'}),
    'sensor': ('sensor_test','VPX11IN3',{'TERM01':'4','TERM02':'1','TERM03':'3','MFG':'KINTO_TEST','CAT':'SENSOR_3WIRE_TEST'}),
}

def device(kind, ident, page, x, y, tag, descriptions):
    """Qualified test symbols and pins; no arbitrary catalog/symbol substitution."""
    from src.tools.delta_mapping import literal
    if kind not in DEVICE_TEMPLATES:raise ValueError('Unqualified device type')
    if not isinstance(descriptions,dict) or set(descriptions)-{'DESC1','DESC2','DESC3'}:raise ValueError('Only device descriptions are configurable')
    for value in descriptions.values():literal(value,'description')
    literal(tag,'device tag')
    role,symbol,attributes=DEVICE_TEMPLATES[kind]
    return dict(id=ident,role=role,symbol=symbol,drawing_page=page,x=x,y=y,attributes={**attributes,'TAG1':tag,**descriptions})

def validate_open_names(open_paths, targets):
    """Electrical project commands can identify drawings by basename."""
    from pathlib import Path
    for target in targets:
        matches=[p for p in open_paths if Path(p).name.casefold()==Path(target).name.casefold()]
        if len(matches)!=1:raise ValueError('Duplicate/missing open drawing filename before batch writes: '+str(target))
