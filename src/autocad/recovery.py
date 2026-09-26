"""Explicit quarantine recovery. Never replays, saves, closes or undoes CAD work."""
import hashlib,json,os,re,subprocess,sys,uuid
from pathlib import Path
from src.autocad.client_gate import gate_path

ROOT=Path(__file__).resolve().parents[2]

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True).encode()).hexdigest()

def probe_worker(expected_drawing_path,expected_instance_hwnd):
    proc=subprocess.run([sys.executable,'-m','src.autocad.recovery_probe'],cwd=ROOT,
        input=json.dumps({'path':expected_drawing_path,'hwnd':expected_instance_hwnd}),capture_output=True,
        text=True,encoding='utf8',timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if proc.returncode:raise ValueError('Recovery read failed: '+proc.stderr[-600:])
    data=json.loads(proc.stdout)
    if not data.get('idle') or not data.get('saved'):raise ValueError('Expected drawing must be saved and CAD idle; no changes made')
    return data

def inspect_or_release(action,expected_drawing_path,expected_instance_hwnd,operation_id='',snapshot_id=''):
    """Release acknowledges a reviewed partial state, NOT success of the failed tool."""
    import msvcrt,win32process
    if action not in {'inspect','release'}:raise ValueError('Expected inspect or release')
    path=Path(expected_drawing_path)
    if not path.is_absolute() or path.suffix.lower()!='.dwg' or not path.is_file():raise ValueError('Explicit existing DWG required')
    if type(expected_instance_hwnd)!=int or expected_instance_hwnd<=0:raise ValueError('Explicit instance HWND required')
    lock=gate_path()
    if not lock.exists():return {'success':True,'status':'no_interruption','cad_contacted':False}
    with lock.open('r+b',buffering=0) as stream:
        try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:return {'success':False,'status':'cad_in_use','submitted':False}
        try:
            stream.seek(1);raw=stream.read()
            if not raw:return {'success':True,'status':'no_interruption','cad_contacted':False}
            marker=json.loads(raw);parts=marker['operation'].rsplit(':',1)
            if len(parts)!=2 or not re.fullmatch('[a-f0-9]{32}',parts[1]):raise ValueError('Unrecognized interruption; retain marker')
            op=parts[1]
            record_path=lock.parent/'operations'/(op+'.json')
            record=json.loads(record_path.read_text(encoding='utf8'))
            if record.get('state')!='outcome_unknown':raise ValueError('Operation not finalized as unknown; retain marker')
            progress=json.loads(record_path.with_suffix('.progress').read_text(encoding='utf8'))
            if not isinstance(progress.get('pid'),int) or progress['pid'] in win32process.EnumProcesses():raise ValueError('Worker may still be alive; retain marker')
            state=probe_worker(str(path),expected_instance_hwnd)
            folder=lock.parent/'recovery';folder.mkdir(exist_ok=True)
            current={'marker_sha256':hashlib.sha256(raw).hexdigest(),'operation_id':op,'state':state,
                     'operation_record_sha256':hashlib.sha256(record_path.read_bytes()).hexdigest()}
            if action=='inspect':
                sid=uuid.uuid4().hex
                receipt=folder/(sid+'.json');receipt.write_text(json.dumps(current,indent=2),encoding='utf8')
                return {'success':True,'status':'review_required','snapshot_id':sid,'operation_id':op,'snapshot':current,
                        'receipt':str(receipt),'failed_tool_result':record.get('result'),
                        'warning':'Review partial objects and receipts. Release only enables NEW operations; never replay the old request.'}
            if not re.fullmatch('[a-f0-9]{32}',snapshot_id) or operation_id!=op:raise ValueError('Exact inspected operation/snapshot required')
            approved=json.loads((folder/(snapshot_id+'.json')).read_text(encoding='utf8'))
            if approved!=current:raise ValueError('State changed since inspection; retain marker and inspect again')
            recovery=folder/(snapshot_id+'-released.json')
            if recovery.exists():raise ValueError('Snapshot already consumed')
            result={'success':True,'status':'released_for_new_operations','operation_id':op,'snapshot':current,
                    'failed_operation_status':'partial_or_unknown','automatic_retry':False,'cad_modified':False}
            recovery.write_text(json.dumps(result,indent=2),encoding='utf8')
            # Durable evidence is written before releasing quarantine.
            stream.seek(1);stream.truncate();os.fsync(stream.fileno())
            result['receipt']=str(recovery);return result
        finally:
            stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
