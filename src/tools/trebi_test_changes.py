"""Restricted native changes for the saved synthetic three-page acceptance project."""
import hashlib,json,re,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
LAMP_SYMBOL=Path("C:/Users/Public/Documents/Autodesk/Acade 2026/Libs/iec2/HLT1R.dwg")

def validate(spec):
    fields={'purpose','action','drawing_sha256','component_handle','wire_handles','peer_handle'}
    if not isinstance(spec,dict) or set(spec)!=fields or spec['purpose']!='test_only' or spec['action'] not in {'lamp_green_to_red','output_y00_to_y01'}:
        raise ValueError('Restricted test_only lamp/channel change required')
    if not isinstance(spec['drawing_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',spec['drawing_sha256']):raise ValueError('Expected saved DWG SHA256 required')
    for handle in [spec['component_handle'],spec['peer_handle']]:
        if not isinstance(handle,str) or not re.fullmatch('[0-9A-Fa-f]+',handle):raise ValueError('Exact entity handles required')
    wires=spec['wire_handles']
    if not isinstance(wires,list) or len(wires)!=(2 if spec['action']=='lamp_green_to_red' else 1) or any(not isinstance(h,str) or not re.fullmatch('[0-9A-Fa-f]+',h) for h in wires) or len({h.upper() for h in wires})!=len(wires):raise ValueError('Exact independent wire handles required')
    return spec

def verify_reconnected_wires(handles, component_handle, peer_handle):
    """Read every new segment after numbering; never infer network identity from cache."""
    from src.tools.native_electrical import inspect_wire
    expected = {(component_handle.upper(), 'X1TERM34'), (peer_handle.upper(), 'X4TERM01')}
    if len(handles) != 3 or len({h.upper() for h in handles}) != 3:
        raise RuntimeError('Expected three distinct output route segments')
    reads = []
    for handle in handles:
        result = inspect_wire(handle)
        endpoints = {(h.upper(), tag) for h, tag in result.get('connections', [])}
        if (not result.get('success') or result.get('wire_number') != 'TEST_DO'
                or result.get('wire_layer') != 'TEST_SIGNAL' or endpoints != expected):
            raise RuntimeError('Numbered output network readback mismatch: ' + handle)
        reads.append(result)
    return {'success': True, 'segments': reads}


from src.autocad.engineering_archive import backup_saved_project

def execute(project_path,drawing_path,spec):
    from src.autocad.connection import get_connection
    from src.autocad.utils import get_block_attributes
    from src.autocad.lisp_bridge import evaluate,literal
    from src.tools.native_electrical import entity,inspect_wire,connect_terminals,set_number
    from src.tools.native_project import guard
    from src.autocad.change_audit import snapshot,verify
    try:
        validate(spec);path=Path(drawing_path)
        if not path.is_absolute() or path.suffix.lower()!='.dwg' or hashlib.sha256(path.read_bytes()).hexdigest()!=spec['drawing_sha256']:raise ValueError('Saved drawing changed')
        conn=get_connection();doc=conn.get_active_document()
        if Path(doc.FullName).resolve()!=path.resolve() or not doc.Saved:raise ValueError('Exact saved active drawing required')
        project=guard(conn,project_path)
        obj=doc.HandleToObject(spec['component_handle']);attrs=get_block_attributes(obj)
        wires=[inspect_wire(h) for h in spec['wire_handles']]
        if any(not w.get('success') for w in wires):raise ValueError('Cannot verify existing wire networks')
        if spec['action']=='lamp_green_to_red':
            if obj.Name.upper()!='HLT1G' or any(attrs.get(k)!=v for k,v in {'TAG1':'-405H1','MFG':'KINTO_TEST','CAT':'LAMP_24V_TEST','COLOR':'GN','TERM01':'1','TERM02':'2'}.items()):raise ValueError('Expected unchanged synthetic green lamp')
            if {w['wire_number'] for w in wires}!={'TEST_DO','TEST0'}:raise ValueError('Lamp networks differ')
            for w in wires:
                own=(obj.Handle.upper(),'X4TERM01' if w['wire_number']=='TEST_DO' else 'X1TERM02')
                if len(w['connections'])!=2 or own not in {(h.upper(),t) for h,t in w['connections']}:raise ValueError('Lamp must have two unbranched verified networks')
            asset=LAMP_SYMBOL
            if not asset.is_file():raise ValueError('Native red lamp symbol absent')
        else:
            peer=doc.HandleToObject(spec['peer_handle']);pa=get_block_attributes(peer)
            if obj.Name!='HBB1_KINTO_R2_EC0902_TEST' or attrs.get('TAG1')!='-300A1' or attrs.get('CAT')!='R2-EC0902D0' or attrs.get('DESC3')!='SYNTHETIC DI DO TEST':raise ValueError('Expected synthetic R2 module')
            if attrs.get('TERM33')!='TB4:Y00' or attrs.get('TERM34')!='TB4:Y01' or attrs.get('X1TERM34'):raise ValueError('Unexpected channel inventory or occupied Y01')
            if peer.Name!='HA1S1' or pa.get('SIGCODE')!='TEST_DO':raise ValueError('Expected output source arrow')
            expected={(obj.Handle.upper(),'X1TERM33'),(peer.Handle.upper(),'X4TERM01')}
            if wires[0]['wire_number']!='TEST_DO' or wires[0]['wire_layer']!='TEST_SIGNAL' or {(h.upper(),t) for h,t in wires[0]['connections']}!=expected:raise ValueError('Output network differs or is branched')
            line=doc.HandleToObject(spec['wire_handles'][0]);start=list(line.StartPoint);end=list(line.EndPoint)
            if line.ObjectName!='AcDbLine' or start[1]!=end[1]:raise ValueError('Only original single horizontal output segment supported')
            # Require the physical candidate point to have no existing attached wire.
            points={a.TagString:list(a.InsertionPoint) for a in obj.GetAttributes() if a.TagString in {'X1TERM33','X1TERM34'}}
            if any(e.ObjectName=='AcDbLine' and any(sum((float(v)-float(p))**2 for v,p in zip(endpoint,points['X1TERM34']))<1e-8 for endpoint in (e.StartPoint,e.EndPoint)) for e in doc.ModelSpace):raise ValueError('Y01 already has geometry attached')
        before_objects=snapshot(doc)
    except Exception as exc:return {'success':False,'submitted':False,'status':'preflight_rejected','error':str(exc)}
    folder=ROOT/'work/changes'/uuid.uuid4().hex;folder.mkdir(parents=True)
    try:
        saved_backup=backup_saved_project(project_path,project,folder/'backup')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=spec['drawing_sha256'] or not doc.Saved:
            raise ValueError('Drawing changed while preparing backup')
        if guard(conn,project_path)!=project:raise ValueError('Project changed while preparing backup')
    except Exception as exc:
        result={'success':False,'submitted':False,'status':'preflight_rejected','error':str(exc),'backup_candidate':str(folder/'backup')}
        (folder/'report.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        return result
    receipt=folder/'report.json';report={'success':False,'submitted':True,'status':'running','steps':[],'spec':spec,'drawing':str(path),'receipt':str(receipt),'backup':saved_backup,'before_attributes':attrs,'before_wires':wires,'before_objects':before_objects,'automatic_retry':False}
    def persist():
        temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2),encoding='utf8');temp.replace(receipt)
    def step(name,call):
        row={'step':name,'status':'entered'};report['steps'].append(row);persist()
        try:
            result=call();row['result']=result
            if isinstance(result,dict) and result.get('success') is False:raise RuntimeError(str(result))
            row['status']='completed';persist();return result
        except Exception as exc:
            row.update(status='failed_or_unknown',error=str(exc));report['failed_step']=name;persist();raise
    def attr(handle,key,value):
        result=evaluate(conn,'(c:wd_modattrval '+entity(handle)+' '+literal(key)+' '+literal(value)+' nil)')
        if result!=1:raise RuntimeError('Attribute update unconfirmed: '+key)
        return result
    try:
        if spec['action']=='lamp_green_to_red':
            swapped=step('native_swap',lambda:evaluate(conn,'(c:wd_bswap '+entity(obj.Handle)+' '+literal(asset.as_posix())+' 24 1 nil nil)'))
            if not isinstance(swapped,list) or len(swapped)!=2 or not isinstance(swapped[0],str) or swapped[1] not in (None,0):raise RuntimeError('Unexpected swap result')
            handle=swapped[0];report['new_handle']=handle;persist()
            step('color',lambda:attr(handle,'COLOR','RD'));step('catalog',lambda:attr(handle,'CAT','LAMP_24V_RED_TEST'))
            new=doc.HandleToObject(handle);actual=get_block_attributes(new)
            wanted={**attrs,'COLOR':'RD','CAT':'LAMP_24V_RED_TEST'}
            if new.Name.upper()!='HLT1R' or any(actual.get(k)!=v for k,v in wanted.items()):raise RuntimeError('Swapped component identity mismatch')
            reads=[step('wire:'+h,lambda h=h:inspect_wire(h)) for h in spec['wire_handles']]
            for old,new in zip(wires,reads):
                expected={(handle.upper() if h.upper()==spec['component_handle'].upper() else h.upper(),t) for h,t in old['connections']}
                if expected!={(h.upper(),t) for h,t in new['connections']} or new['wire_number']!=old['wire_number']:raise RuntimeError('Swap changed wire network')
            report['after_wires']=reads
        else:
            midpoint=[(a+b)/2 for a,b in zip(start,end)]
            step('trim_original_wire',lambda:evaluate(conn,'(progn (c:wd_trimwire '+entity(spec['wire_handles'][0])+' '+literal(midpoint)+') T)'))
            if evaluate(conn,'(if (entget '+entity(spec['wire_handles'][0])+') T nil)'):raise RuntimeError('Original wire still exists; stop without reconnecting')
            step('clear_old_pin_cache',lambda:attr(obj.Handle,'X1TERM33',''))
            wire=step('connect_y01',lambda:connect_terminals(obj.Handle,'X1TERM34',peer.Handle,'X4TERM01',wire_layer='TEST_SIGNAL'))
            report['new_wire']=wire;persist()
            expected={(obj.Handle.upper(),'X1TERM34'),(peer.Handle.upper(),'X4TERM01')}
            if {(h.upper(),t) for h,t in wire['connections']}!=expected:raise RuntimeError('Reconnected network contains unexpected terminal')
            step('restore_number',lambda:set_number(wire['wire_handles'][0],'TEST_DO'))
            report['after_wire_verification']=step('verify_numbered_output',lambda:verify_reconnected_wires(wire['wire_handles'],obj.Handle,peer.Handle))
            actual=get_block_attributes(obj)
            if actual.get('X1TERM33') or actual.get('X1TERM34')!='TEST_DO':raise RuntimeError('Pin cache mismatch after reconnect')
        after_objects=snapshot(doc);report['after_objects']=after_objects
        report['change_audit']=step('verify_object_changes',lambda:verify(before_objects,after_objects,spec,report))
        if guard(conn,project_path)!=project:raise RuntimeError('Project membership changed')
        step('save',lambda:doc.Save() or {'success':bool(doc.Saved)})
        report.update(success=True,status='native_change_readback_verified',production_ready=False,save_reopen='pending_independent_verification')
    except Exception as exc:report.update(status='partial_or_unknown',error=str(exc))
    finally:persist()
    return report
