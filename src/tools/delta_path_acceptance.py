"""Recompute P0 acceptance from a batch receipt; no visual/native success inferred."""
from collections import defaultdict
from src.tools.delta_batch import verify_insert
from src.tools.trebi_batch import verify_wire_readback

def resolve_connector_network(link, report, logical_page):
    """Cross-check native From/To handles against native wire-network membership.

    Electrical 2026 can omit parametric P/J endpoints from cmpconlst even when
    the native report includes them. Never infer a connection from the plan or
    from geometric proximity. Retain the original snapshot as evidence.
    """
    raw=report['final_wires'][link['id']]
    segments={h.upper() for h in raw.get('network_wire_handles',[])}
    if not segments:raise ValueError('Missing native wire membership: '+link['id'])
    def handle(value):return value[2:].upper() if value.startswith('h=') else ''
    rows=[row for row in report['reports']['from_to']['rows'] if len(row)>49 and row[11]==logical_page and row[12]==logical_page and
          ({handle(row[48]),handle(row[49])} & segments)]
    if len(rows)!=1:raise ValueError('Ambiguous/missing native connector path: '+link['id'])
    row=rows[0]
    if not {handle(row[48]),handle(row[49])} <= segments:raise ValueError('From/To leaves the native wire network')
    expected={}
    for side in ('from','to'):
        id=link[side+'_id'];ent=report['entities'][id];a=report['references'][id]
        points=[p for p in ent['connection_points'] if p['connection']==link[side+'_connection']]
        if len(points)!=1 or not points[0]['terminal']:raise ValueError('Missing endpoint pin identity')
        expected[(ent['handle'].upper(),a.get('TAG1') or a.get('TAGSTRIP') or a.get('TAG2'),points[0]['terminal'])]=link[side+'_connection']
    actual={(handle(row[39]),row[2],row[3]),(handle(row[40]),row[5],row[6])}
    if actual!=set(expected):raise ValueError('Native connector endpoint identity mismatch')
    if row[0]!=raw.get('wire_number') or row[7]!=raw.get('wire_layer') or row[8]!=raw.get('wire_layer'):raise ValueError('Native connector wire number/layer mismatch')
    resolved={(h,expected[(h,tag,pin)]) for h,tag,pin in actual}
    if not {(h.upper(),pin) for h,pin in raw.get('connections',[])} <= resolved:raise ValueError('Unexpected raw native endpoint')
    return {**raw,'connections':sorted(resolved),'endpoint_evidence':'native_from_to_and_network_handles'}

def verify_native(recipe,report):
    entities=report['entities'];attrs=report['references'];wires=report['final_wires']
    verify_insert(entities['r2'])
    for page in recipe['pages']['logical_pages']:
        expected={entities[c['id']]['handle'].upper() for c in recipe['components']+recipe['cable_markers'] if c['drawing_page']==page and any(c['attributes'].get(k) for k in ('TAG1','TAG2','TAGSTRIP'))}
        inventory=report['device_inventory'][page]
        actual=[r['handle'].upper() for r in inventory]
        if len(actual)!=len(expected) or set(actual)!=expected:raise ValueError('Unexpected/missing native tagged device on page '+page)
    parents=defaultdict(list)
    for c in recipe['components']:
        if c['attributes'].get('TAG1'):parents[c['attributes']['TAG1'].casefold()].append(c['id'])
    for ids in parents.values():
        if len(ids)>1 and set(ids)!={'button','lamp'}:raise ValueError('Duplicate device tag')

    for c in recipe['components']+recipe['cable_markers']:
        a=attrs[c['id']]
        if any(a.get(k)!=v for k,v in c['attributes'].items()):raise ValueError('Final attribute mismatch: '+c['id'])
    for side,prefix,suffix in [('socket','X4','J'),('plug','X1','P')]:
        actual=attrs[side]
        points=entities[side]['connection_points']
        expected={f'{prefix}TERM{i+1:02d}{suffix}':r['socket_pin'] for i,r in enumerate(recipe['routes'])}
        if len(points)!=4 or {p['connection']:p['terminal'] for p in points}!=expected:raise ValueError('Missing/wrong connector pin: '+side)
        if any(actual.get('TERM'+p[len(prefix+'TERM'):])!=pin for p,pin in expected.items()):raise ValueError('Final connector pin changed')
    # wd_get_wire_netlst stops at each terminal side; native networks are segments.
    # Terminal-through continuity belongs to the route model, not fabricated native nodes.
    graph=defaultdict(set)
    def node(id,pin):return (entities[id]['drawing'].casefold(),entities[id]['handle'].upper(),pin)
    for w in recipe['connections']:
        a=node(w['from_id'],w['from_connection']);b=node(w['to_id'],w['to_connection']);graph[a].add(b);graph[b].add(a)
    for w in recipe['connections']:
        actual=resolve_connector_network(w,report,next(c['drawing_page'] for c in recipe['components'] if c['id']==w['from_id'])) if {'socket','plug'}.intersection({w['from_id'],w['to_id']}) else wires[w['id']]
        verify_wire_readback(w,entities,actual,w.get('wire_number'))
        start=node(w['from_id'],w['from_connection']);seen=set();todo=[start]
        while todo:
            n=todo.pop()
            if n not in seen:seen.add(n);todo.extend(graph[n]-seen)
        got={(entities[w['from_id']]['drawing'].casefold(),h.upper(),tag) for h,tag in actual['connections']}
        if got!=seen:raise ValueError('Unexpected/missing endpoint (possible short): '+w['id'])
    for ref in recipe['expected_references']:
        if attrs[ref['id']].get(ref['field'])!=ref['value']:raise ValueError('Cross reference mismatch')
    rows=report['reports']['from_to']['rows']
    for r in recipe['routes']:
        matches=[row for row in rows if len(row)>14 and row[13]==r['cable'] and row[14]==r['core']]
        endpoints={(r['strip'],r['terminal']),(r['socket'],r['socket_pin'])}
        if len(matches)!=1 or {(matches[0][2],matches[0][3]),(matches[0][5],matches[0][6])}!=endpoints:raise ValueError('Cable From/To mismatch: '+r['id'])
        matches=[row for row in rows if len(row)>6 and {(row[2],row[3]),(row[5],row[6])}=={(r['plug'],r['plug_pin']),(r['device'],r['device_terminal'])}]
        if len(matches)!=1:raise ValueError('Field From/To mismatch: '+r['id'])
    for k in ('bom','from_to','terminal_plan','terminal_numbers'):
        if not report['reports'][k].get('success') or not report['reports'][k].get('rows'):raise ValueError('Missing native report: '+k)
    for c in recipe['components']+recipe['cable_markers']:
        a=c['attributes']
        if 'CAT' not in a:continue
        matches=[r for r in report['reports']['bom']['rows'] if len(r)>15 and (r[3],r[4],r[15])==(a['CAT'],a['MFG'],a.get('TAG1'))]
        if len(matches)!=1 or matches[0][1]!='1':raise ValueError('BOM part/quantity mismatch: '+c['id'])
    terminal_rows=report['reports']['terminal_plan']['rows']
    for r in recipe['routes']:
        if not any(len(row)>12 and (row[10],row[12])==(r['strip'],r['terminal']) for row in terminal_rows):raise ValueError('Missing strip terminal in native report')
    return {'success':True,'status':'bounded_native_paths_verified','routes':4,'connector_halves':2,'cable_cores':4,'r2_points':76,'wire_networks':len(wires),
        'mating':'declared socket/plug pin pairs; no fictitious jumper wires','production_ready':False}

def review_evidence(data,subjects):
    import json
    from pathlib import Path
    from src.autocad.engineering_archive import digest
    from src.tools.delta_full_paths import plan
    if data.get('schema_version')!=1 or data.get('subjects')!=subjects:raise ValueError('P0 evidence belongs to another or modified project version')
    source=Path(data['receipt_path'])
    if not source.is_absolute() or digest(source)!=data['receipt_sha256']:raise ValueError('Missing or changed P0 receipt')
    receipt=json.loads(source.read_text(encoding='utf8'))
    if receipt.get('status')!='native_readback_verified' or receipt.get('success') is not True:raise ValueError('P0 native batch did not complete')
    if receipt.get('subjects')!=subjects:raise ValueError('P0 receipt is not bound to current saved project')
    recipe=plan(receipt['spec']);result=verify_native(recipe,receipt)
    return {**result,'receipt':str(source),'pending':[p for p in recipe['binding']['pending'] if p!='Native Delta symbol and batch acceptance required'],'independent_reopen_and_pdf_required':True}
