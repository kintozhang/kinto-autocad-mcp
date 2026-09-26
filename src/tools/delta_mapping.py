"""Version 2 localization records keep original and replacement identities separate."""
from src.autocad.delta_esi import inspect_esi, match_identity

def fields(value, required, label):
    if not isinstance(value,dict) or set(value)!=set(required):
        raise ValueError('Exact '+label+' fields required: '+', '.join(required))

def literal(value, label, nullable=False):
    if nullable and value is None:
        return value
    if not isinstance(value,str) or not value.strip() or len(value)>500 or any(ord(c)<32 for c in value):
        raise ValueError('Explicit '+label+' text required')
    return value

def plan_v2(spec):
    from src.tools.delta_io import plan
    fields(spec, ['schema_version','esi','modules','signals'], 'version 2')
    fields(spec['esi'], ['path','sha256'], 'ESI')
    esi = inspect_esi(spec['esi']['path'],spec['esi']['sha256'])
    if not isinstance(spec['modules'],list) or not 1<=len(spec['modules'])<=16:
        raise ValueError('Expected 1..16 modules')
    if not isinstance(spec['signals'],list) or not 1<=len(spec['signals'])<=1024:
        raise ValueError('Expected 1..1024 signals')
    reduced={'schema_version':1,'modules':[],'signals':[]}
    module_states={}; pending=[]; stations=set()
    for m in spec['modules']:
        fields(m,['id','model','input_mode','observed_identity','station'], 'module')
        literal(m['id'],'module id')
        reduced['modules'].append({k:m[k] for k in ('id','model','input_mode')})
        state={'identity_match':None,'station':m['station']}
        if m['observed_identity'] is None:
            pending.append(m['id']+': hardware identity observation missing')
        else:
            state['identity_match']=match_identity(esi,m['observed_identity'])
        if m['station'] is None:
            pending.append(m['id']+': actual station mapping missing')
        else:
            fields(m['station'],['position','source'],'station')
            pos=m['station']['position']
            if type(pos) is not int or not 1<=pos<=65535 or pos in stations:
                raise ValueError('Unique positive station positions required')
            stations.add(pos);literal(m['station']['source'],'station source')
        module_states[m['id'].casefold()]=state
    addresses=set()
    for s in spec['signals']:
        fields(s,['id','target','direction','purpose','original','potential','wire_number','plc_address','evidence'], 'signal')
        fields(s['target'],['module_id','port','channel'],'target')
        fields(s['original'],['signal','terminal','page'],'original')
        literal(s['id'],'signal id')
        literal(s['original']['signal'],'original signal')
        for k in ('terminal','page'):
            literal(s['original'][k],'original '+k,True)
            if s['original'][k] is None:pending.append(s['id']+': original '+k+' missing')
        for k in ('potential','wire_number'):
            literal(s[k],k,True)
            if s[k] is None:pending.append(s['id']+': '+k+' missing')
        if not isinstance(s['evidence'],list) or len(s['evidence'])>32:
            raise ValueError('Evidence must be a bounded list')
        for ref in s['evidence']:literal(ref,'evidence')
        if not s['evidence']:pending.append(s['id']+': signal evidence missing')
        if s['plc_address'] is None:
            pending.append(s['id']+': NC50 address missing')
        else:
            fields(s['plc_address'],['value','source'],'PLC address')
            literal(s['plc_address']['value'],'PLC address');literal(s['plc_address']['source'],'PLC address source')
            address=s['plc_address']['value'].strip().casefold()
            if address in addresses:raise ValueError('Duplicate NC50 address')
            addresses.add(address)
        reduced['signals'].append({'id':s['id'],**s['target'],'direction':s['direction'],
            'purpose':s['purpose'],'potential':s['potential'] or '__UNCONFIRMED_SUPPLY__','source_signal':s['original']['signal']})
    result=plan(reduced)
    for original, target in zip(spec['signals'],result['signals']):
        target.update(original=dict(original['original']),potential=original['potential'],wire_number=original['wire_number'],
                      plc_address=original['plc_address'],evidence=list(original['evidence']))
        target['global_plc_address']=None if original['plc_address'] is None else original['plc_address']['value']
        if original['potential'] is None and original['direction']=='output':target['common_connection_draft']=None
    result.update(schema_version=2,esi=esi,module_evidence=module_states,status='localization_draft_checked',
        mapping_complete=not pending,ready_for_drawing=False,pending=pending+['Native Delta symbol and batch acceptance required'],
        limitations=['Identity matching checks supplied observations; this tool does not read hardware',
                     'Explicit PLC addresses are recorded, not independently verified against NC50',
                     'Process image offsets and byte-internal bits remain unverified',
                     'No CAD writes; no automatic conversion to a production drawing'])
    return result
