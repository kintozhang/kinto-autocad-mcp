"""Offline check of native terminal networks. Not a safety performance assessment."""
def verify(channels, readbacks):
    if not isinstance(channels,dict) or len(channels)<2:raise ValueError('At least two explicit channels required')
    seen_nodes=set();seen_wires=set();checked=0
    for name,nets in channels.items():
        if not nets:raise ValueError('Empty channel '+name)
        own_nodes=set();own_wires=set()
        for net in nets:
            h=net['wire_handle'].upper()
            if h in own_wires or h in seen_wires:raise ValueError('Repeated/shared wire '+h)
            row=readbacks[h]
            if row.get('success') is not True or row['wire_handle'].upper()!=h:raise ValueError('Missing verified readback')
            expected={tuple(v) for v in net['nodes']}
            actual={tuple(v) for v in row['connections']}
            if len(expected)<2 or actual!=expected:raise ValueError('Missing or unexpected terminal on '+h)
            own_nodes|=actual;own_wires.add(h);checked+=1
        if own_nodes & seen_nodes:raise ValueError('Channels share a terminal')
        seen_nodes|=own_nodes;seen_wires|=own_wires
    return {'success':True,'channels':len(channels),'networks':checked,'native_terminal_separation':True,
            'safety_function_validated':False,'fault_detection_validated':False,'production_ready':False}
