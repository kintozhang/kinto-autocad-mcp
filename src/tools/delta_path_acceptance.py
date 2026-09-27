"""Recompute P0 acceptance from a batch receipt; no visual/native success inferred."""
from collections import defaultdict
from src.tools.delta_batch import verify_insert
from src.tools.trebi_batch import verify_wire_readback

def resolve_connector_network(link, report, logical_page, expected_nodes=None):
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
    if expected_nodes is None:
        expected_nodes={(link[side+'_id'],link[side+'_connection']) for side in ('from','to')}
    expected={}
    for ident,pin in expected_nodes:
        ent=report['entities'][ident];attrs=report['references'][ident]
        points=[p for p in ent['connection_points'] if p['connection']==pin]
        if len(points)!=1 or not points[0]['terminal']:raise ValueError('Missing endpoint pin identity')
        expected[(ent['handle'].upper(),attrs.get('TAG1') or attrs.get('TAGSTRIP') or attrs.get('TAG2'),points[0]['terminal'])]=pin
    if not rows:raise ValueError('Ambiguous/missing native connector path: '+link['id'])
    edges=set();actual=set();graph=defaultdict(set)
    for row in rows:
        if not {handle(row[48]),handle(row[49])} <= segments:raise ValueError('From/To leaves the native wire network')
        ends=((handle(row[39]),row[2],row[3]),(handle(row[40]),row[5],row[6]))
        if ends[0]==ends[1] or not set(ends)<=set(expected):raise ValueError('Native connector endpoint identity mismatch')
        edge=frozenset(ends)
        if edge in edges:raise ValueError('Duplicate/ambiguous native network path')
        edges.add(edge);actual.update(ends);graph[ends[0]].add(ends[1]);graph[ends[1]].add(ends[0])
        if row[0]!=raw.get('wire_number') or row[7]!=raw.get('wire_layer') or row[8]!=raw.get('wire_layer'):raise ValueError('Native connector wire number/layer mismatch')
    seen=set();todo=[next(iter(actual))]
    while todo:
        node=todo.pop()
        if node not in seen:seen.add(node);todo.extend(graph[node]-seen)
    if seen!=set(expected) or actual!=set(expected) or len(edges)!=len(expected)-1:
        raise ValueError('Disconnected or ambiguous native branch network')
    resolved={(h,expected[(h,tag,pin)]) for h,tag,pin in actual}
    if not {(h.upper(),pin) for h,pin in raw.get('connections',[])} <= resolved:raise ValueError('Unexpected raw native endpoint')
    return {**raw,'connections':sorted(resolved),'endpoint_evidence':'native_from_to_and_network_handles'}


def verify_signal_path(recipe,report,code):
    """Signal arrows have no pin identity; native From/To passes through them.

    Require exactly one native row joining the two real (non-arrow) endpoints
    across pages, over segments drawn only from both arrow-ended networks.
    """
    comps={c['id']:c for c in recipe['components']}
    arrows={c['role']:c['id'] for c in comps.values() if c.get('signal_code')==code}
    if set(arrows)!={'source','destination'}:raise ValueError('Incomplete signal arrow pair: '+code)
    sides=[]
    for role in ('source','destination'):
        links=[w for w in recipe['connections'] if arrows[role] in (w['from_id'],w['to_id'])]
        if len(links)!=1:raise ValueError('Ambiguous signal arrow wiring: '+code)
        w=links[0];far='to' if w['from_id']==arrows[role] else 'from'
        ident,pin=w[far+'_id'],w[far+'_connection']
        if comps.get(ident,{}).get('signal_code'):raise ValueError('Signal arrow wired to arrow: '+code)
        raw=report['final_wires'][w['id']]
        segments={h.upper() for h in raw.get('network_wire_handles',[])}
        if not segments:raise ValueError('Missing native wire membership: '+w['id'])
        ent=report['entities'][ident];attrs=report['references'][ident]
        points=[p for p in ent['connection_points'] if p['connection']==pin]
        if len(points)!=1 or not points[0]['terminal']:raise ValueError('Missing endpoint pin identity')
        sides.append(dict(wire=w,raw=raw,segments=segments,page=comps[arrows[role]]['drawing_page'],
                          end=(ent['handle'].upper(),attrs.get('TAG1') or attrs.get('TAGSTRIP') or attrs.get('TAG2'),points[0]['terminal'])))
    def handle(value):return value[2:].upper() if value.startswith('h=') else ''
    allowed=sides[0]['segments']|sides[1]['segments']
    rows=[row for row in report['reports']['from_to']['rows'] if len(row)>49 and {handle(row[48]),handle(row[49])}&allowed]
    if len(rows)!=1:raise ValueError('Ambiguous/missing native signal path: '+code)
    row=rows[0];used={handle(row[48]),handle(row[49])}
    if not used<=allowed or not all(used&s['segments'] for s in sides):raise ValueError('Native signal path leaves arrow networks: '+code)
    ends={(handle(row[39]),row[2],row[3],row[11]),(handle(row[40]),row[5],row[6],row[12])}
    if ends!={(*s['end'],s['page']) for s in sides}:raise ValueError('Native signal path endpoint mismatch: '+code)
    for s in sides:
        if row[0]!=s['wire'].get('wire_number') or row[0]!=s['raw'].get('wire_number') or row[7]!=s['raw'].get('wire_layer') or row[8]!=s['raw'].get('wire_layer'):
            raise ValueError('Native signal path wire number/layer mismatch: '+code)
    return {'signal_code':code,'endpoints':sorted(ends),'segments':sorted(used)}


def verify_native(recipe,report):
    entities=report['entities'];attrs=report['references'];wires=report['final_wires']
    verify_insert(entities['r2'])
    for page in recipe['pages']['logical_pages']:
        expected={entities[c['id']]['handle'].upper() for c in recipe['components']+recipe['cable_markers'] if c['drawing_page']==page and any(c['attributes'].get(k) for k in ('TAG1','TAG2','TAGSTRIP'))}
        inventory=report['device_inventory'][page]
        actual=[r['handle'].upper() for r in inventory]
        if len(actual)!=len(expected) or set(actual)!=expected:raise ValueError('Unexpected/missing native tagged device on page '+page)
    if recipe.get('nc50_test_plan'):
        for id in ('button','lamp','r2'):
            component=next(c for c in recipe['components'] if c['id']==id)
            expected=component['attributes']
            rows=[row for row in report['reports']['bom']['rows'] if len(row)>22 and row[22].upper()=='H='+entities[id]['handle'].upper()]
            if len(rows)!=1 or rows[0][15]!=expected['TAG1'] or rows[0][3]!=expected['CAT']:
                raise ValueError('Missing/ambiguous native candidate BOM component: '+id)
            if rows[0][16:19]!=[attrs[id].get(k,'') for k in ('DESC1','DESC2','DESC3')]:
                raise ValueError('Native candidate BOM descriptions mismatch: '+id)
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
        if len(points)!=len(recipe['routes']) or {p['connection']:p['terminal'] for p in points}!=expected:raise ValueError('Missing/wrong connector pin: '+side)
        if any(actual.get('TERM'+p[len(prefix+'TERM'):])!=pin for p,pin in expected.items()):raise ValueError('Final connector pin changed')
    # wd_get_wire_netlst stops at each terminal side; native networks are segments.
    # Terminal-through continuity belongs to the route model, not fabricated native nodes.
    arrow_ids={c['id'] for c in recipe['components'] if c.get('signal_code')}
    graph=defaultdict(set)
    def node(id,pin):return (entities[id]['drawing'].casefold(),entities[id]['handle'].upper(),pin)
    for w in recipe['connections']:
        a=node(w['from_id'],w['from_connection']);b=node(w['to_id'],w['to_connection']);graph[a].add(b);graph[b].add(a)
    for w in recipe['connections']:
        start=node(w['from_id'],w['from_connection']);seen=set();todo=[start]
        while todo:
            n=todo.pop()
            if n not in seen:seen.add(n);todo.extend(graph[n]-seen)
        expected_nodes={(ident,pin) for ident,ent in entities.items() for drawing,h,pin in seen if ent['drawing'].casefold()==drawing and ent['handle'].upper()==h}
        # Arrow-ended links: raw network readback here, cross-page path via verify_signal_path.
        use_reports=(recipe.get('native_path_acceptance') and not {w['from_id'],w['to_id']}&arrow_ids) or {'socket','plug'}.intersection({w['from_id'],w['to_id']})
        actual=resolve_connector_network(w,report,next(c['drawing_page'] for c in recipe['components'] if c['id']==w['from_id']),expected_nodes) if use_reports else wires[w['id']]
        verify_wire_readback(w,entities,actual,w.get('wire_number'))
        got={(entities[w['from_id']]['drawing'].casefold(),h.upper(),tag) for h,tag in actual['connections']}
        if got!=seen:raise ValueError('Unexpected/missing endpoint (possible short): '+w['id'])
    signal_paths=[verify_signal_path(recipe,report,code) for code in sorted({c['signal_code'] for c in recipe['components'] if c.get('signal_code')})] if recipe.get('native_path_acceptance') else []
    for ref in recipe['expected_references']:
        if attrs[ref['id']].get(ref['field'])!=ref['value']:raise ValueError('Cross reference mismatch')
    rows=report['reports']['from_to']['rows']
    for r in recipe['routes']:
        matches=[row for row in rows if len(row)>14 and row[13]==r['cable'] and row[14]==r['core']]
        endpoints={(r['strip'],r['terminal']),(r['socket'],r['socket_pin'])}
        if len(matches)!=1 or {(matches[0][2],matches[0][3]),(matches[0][5],matches[0][6])}!=endpoints:raise ValueError('Cable From/To mismatch: '+r['id'])
        matches=[row for row in rows if len(row)>6 and {(row[2],row[3]),(row[5],row[6])}=={(r['plug'],r['plug_pin']),(r['device'],r['device_terminal'])}]
        if not recipe.get('native_path_acceptance') and len(matches)!=1:raise ValueError('Field From/To mismatch: '+r['id'])
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
    return {'success':True,'status':'bounded_native_paths_verified','routes':len(recipe['routes']),'connector_halves':2,'cable_cores':len(recipe['cable_markers']),'r2_points':76,'wire_checks':len(wires),'wire_networks':len({(entities[w['from_id']]['drawing'].casefold(),tuple(sorted(wires[w['id']].get('network_wire_handles') or [w['id']]))) for w in recipe['connections']}),
        'signal_paths':signal_paths,'mating':'declared socket/plug pin pairs; no fictitious jumper wires','production_ready':False}

def review_evidence(data,subjects):
    import json
    from pathlib import Path
    from src.autocad.engineering_archive import digest
    from src.tools.trebi_batch import plan
    if data.get('schema_version')!=1 or data.get('subjects')!=subjects:raise ValueError('P0 evidence belongs to another or modified project version')
    source=Path(data['receipt_path'])
    if not source.is_absolute() or digest(source)!=data['receipt_sha256']:raise ValueError('Missing or changed P0 receipt')
    receipt=json.loads(source.read_text(encoding='utf8'))
    if receipt.get('status')!='native_readback_verified' or receipt.get('success') is not True:raise ValueError('P0 native batch did not complete')
    if receipt.get('subjects')!=subjects:raise ValueError('P0 receipt is not bound to current saved project')
    recipe=plan(receipt['spec']);result=verify_native(recipe,receipt)
    if receipt['spec'].get('schema_version')==5:
        reopened=receipt.get('independent_reopen',{})
        if reopened.get('success') is not True or reopened.get('subjects')!=subjects:
            raise ValueError('Missing current-version native reopen evidence')
        verify_native(recipe,reopened['snapshot'])
    categories=['tag_uniqueness','connections','cross_references','bom','terminals']
    if receipt['spec'].get('schema_version')==5:categories.append('save_reopen')
    return {**result,'verified_categories':categories,'receipt_sha256':digest(source),'receipt':str(source),'pending':[p for p in recipe['binding']['pending'] if p!='Native Delta symbol and batch acceptance required'],'independent_reopen_and_pdf_required':True}
