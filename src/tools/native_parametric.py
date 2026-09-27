"""Restricted test inserts using locally documented Electrical 2026 APIs."""
from pathlib import Path
import re
from src.autocad.lisp_bridge import evaluate,literal
from src.autocad.connection import get_connection
from src.autocad.utils import get_block_attributes
from src.tools.native_project import guard
from src.tools.native_electrical import _points

def connector_params(pins):
    if not isinstance(pins,list) or not 1<=len(pins)<=8 or any(not isinstance(p,str) or not re.fullmatch('[A-Za-z0-9_-]{1,8}',p) for p in pins) or len(set(pins))!=len(pins):
        raise ValueError('One to eight distinct literal pin labels required')
    return [1,2,1,2,1,0,0,1,1,20.,7.,7.,7.,7.,2.,len(pins),','.join(pins),0,0]

def place_plc_addresses(block):
    """Separate address labels from adjacent terminal numbers at 10 mm pitch."""
    for attribute in block.GetAttributes():
        if attribute.TagString.startswith('TAGA'):
            from win32com.client import VARIANT
            import pythoncom
            point=list(attribute.TextAlignmentPoint)
            point[0] += 15.0
            attribute.TextAlignmentPoint=VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, point)
            attribute.Update()


def insert(kind,project_path,drawing_path,x,y,purpose,pins=None):
    entered=False;created=[]
    try:
        if purpose!='test_only':raise ValueError('Only isolated test_only fixtures are supported')
        params=connector_params(pins) if kind=='connector' else None
        if kind not in {'connector','plc_fixture'}:raise ValueError('Unknown kind')
        xy=literal([x,y,0]);conn=get_connection();guard(conn,project_path);doc=conn.get_active_document()
        if Path(doc.FullName).resolve()!=Path(drawing_path).resolve() or not doc.Saved:raise ValueError('Exact saved test drawing required')
        before={e.Handle for e in doc.ModelSpace}
        blocks=[e.Name for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference']
        if sorted(blocks)!=['KINTO_TREBI_ELECTRICAL_A3','WD_M']:raise ValueError('Requires blank TREBI page; never insert over existing components')
        if kind=='connector':
            expression="(mapcar '(lambda (e) (cdr (assoc 5 (entget e)))) (c:ace_ins_parametric_connector "+xy+' 1.0 '+literal(params)+'))'
        else:
            expression='(progn (c:wd_inplc_nd '+xy+' "2" "I:10010" nil 10 1 99 10.0 "V" (c:wd_find_sel_plc "1771-IAD") (list "" "TEST" "" "TEST")) T)'
        entered=True;handles=evaluate(conn,expression,timeout=75)
        created=[e.Handle for e in doc.ModelSpace if e.Handle not in before]
        if kind=='plc_fixture':
            handles=[h for h in created if doc.HandleToObject(h).ObjectName=='AcDbBlockReference' and doc.HandleToObject(h).Name.startswith('PLCIO')]
        if not handles or any(h not in created for h in handles):raise ValueError('Native insert did not identify new entities')
        rows=[]
        for h in handles:
            e=doc.HandleToObject(h)
            if e.ObjectName!='AcDbBlockReference':raise ValueError('Expected native block')
            if kind=='plc_fixture':place_plc_addresses(e)
            rows.append({'handle':h,'block':e.Name,'attributes':get_block_attributes(e),'connection_points':_points(e)})
        if kind=='connector' and len(rows[0]['connection_points'])!=2*len(pins):raise ValueError('Missing connector pins')
        if kind=='plc_fixture' and (len(rows)!=1 or len(rows[0]['connection_points'])!=17 or len([k for k in rows[0]['attributes'] if k.startswith('TAGA')])!=16):raise ValueError('Incomplete PLC fixture')
        return {'success':True,'status':'native_attributes_read_back','objects':rows,'created_handles':created,
                'kind':kind,'production_ready':False,'note':'Test insertion only; reports, wiring and reopen still required. PLC fixture is Allen-Bradley 1771-IAD, NOT Delta R2.'}
    except Exception as exc:
        if entered:
            try:created=[e.Handle for e in doc.ModelSpace if e.Handle not in before]
            except Exception:pass
        return {'success':False,'status':'partial_or_unknown' if entered else 'preflight_rejected','submitted':entered,
                'created_handles':created,'error':str(exc),'automatic_retry':False}


def insert_connector_half(x,y,side,pins,attributes):
    """Two separate supported calls replace type=2 (2026 reports not implemented)."""
    from src.autocad.com_runtime import read_call
    from src.tools.native_electrical import entity
    created=None
    try:
        if side not in {'plug','socket'}:raise ValueError('Explicit plug/socket required')
        params=connector_params(pins);params[0]=4 if side=='plug' else 8
        params[1]=1;params[3]=1;params[9]=40.
        if set(attributes)!={'TAG1','MFG','CAT','DESC1'}:raise ValueError('Controlled connector attributes required')
        for value in attributes.values():literal(value)
        conn=get_connection();doc=conn.get_active_document();before=read_call(lambda:{e.Handle for e in doc.ModelSpace})
        handles=evaluate(conn,"(progn (c:ace_gbl_wd_m 1) (mapcar '(lambda (e) (cdr (assoc 5 (entget e)))) (c:ace_ins_parametric_connector "+literal([x,y,0])+' 1.0 '+literal(params)+')))',timeout=75)
        if not isinstance(handles,list) or len(handles)!=1 or handles[0] in before:raise RuntimeError('Native connector did not return one new block')
        created=handles[0]
        from src.autocad.com_runtime import wait_for_document
        wait_for_document(conn.get_application(),read_call(lambda:doc.FullName))
        obj=read_call(lambda:doc.HandleToObject(created))
        for key,value in attributes.items():
            if evaluate(conn,'(c:wd_modattrval '+entity(created)+' '+literal(key)+' '+literal(value)+' nil)')!=1:raise RuntimeError('Connector attribute update failed: '+key)
        actual=read_call(lambda:get_block_attributes(obj));points=read_call(lambda:_points(obj))
        prefix='X1' if side=='plug' else 'X4';suffix='P' if side=='plug' else 'J'
        expected={f'{prefix}TERM{i+1:02d}{suffix}':pin for i,pin in enumerate(pins)}
        if len(points)!=len(pins) or {p['connection']:p['terminal'] for p in points}!=expected:raise RuntimeError('Connector pin readback mismatch')
        if any(actual.get(k)!=v for k,v in attributes.items()):raise RuntimeError('Connector identity readback mismatch')
        return {'success':True,'handle':created,'block':read_call(lambda:obj.Name),'attributes':actual,'connection_points':points,'api':'c:ace_ins_parametric_connector','side':side}
    except Exception as exc:
        return {'success':False,'created_handle':created,'error':str(exc),'automatic_retry':False}
