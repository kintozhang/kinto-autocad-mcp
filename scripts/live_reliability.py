"""Explicit synthetic-only acceptance; never save or close the user's drawing."""
import asyncio, hashlib, json, sys, time
from datetime import datetime, timedelta
from pathlib import Path
import pythoncom
import win32com.client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.client_gate import exclusive
from src.autocad.com_runtime import ComBusyError, read_call, document_full_name, wait_for_document, lookup_document_open
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate

ROOT=Path(__file__).resolve().parents[1]
protected=Path('C:/Users/James/Desktop/NEW-MACH647_name plate+CE.dwg')
out=ROOT/'work/acceptance'/('reliability-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True,exist_ok=False)
target=out/'test.dwg'
def fingerprint():
    return {'sha256':hashlib.sha256(protected.read_bytes()).hexdigest(),'mtime_ns':protected.stat().st_mtime_ns,'size':protected.stat().st_size}
report={'test_dwg':str(target),'protected':str(protected),'before':fingerprint(),'status':'started'}
pythoncom.CoInitialize()
try:
    with exclusive('reliability-test-create'):
        app=win32com.client.GetActiveObject('AutoCAD.Application')
        hwnd=read_call(lambda:int(app.HWND))
        original=next(app.Documents.Item(i) for i in range(app.Documents.Count)
                      if Path(app.Documents.Item(i).FullName).resolve()==protected.resolve())
        report['original_path']=original.FullName
        report['original_saved']=read_call(lambda:bool(original.Saved))
        report['original_count']=read_call(lambda:int(original.ModelSpace.Count))
        previous_name=read_call(lambda:app.ActiveDocument.Name)
        app.Documents.Add()  # Submit exactly once; returned dispatch may be untyped.
        deadline=time.monotonic()+8
        while True:
            try:
                candidate=app.ActiveDocument
                if (candidate.Name != previous_name and candidate.FullName == ''
                        and bool(app.GetAcadState().IsQuiescent)
                        and int(candidate.GetVariable('CMDACTIVE')) == 0):
                    doc=candidate
                    break
            except (AttributeError, ComBusyError):
                pass
            if time.monotonic()>=deadline:
                raise RuntimeError('New test document not ready; Add was not retried')
            time.sleep(.15)
        doc.SaveAs(str(target))
        wait_for_document(app,target)
    def guard():
        if Path(document_full_name(app)).resolve()!=target.resolve() or int(app.HWND)!=hwnd:
            raise RuntimeError('Wrong active test target')
    async def exercise():
        params=StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT))
        async with stdio_client(params) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=60)) as session:
                await session.initialize()
                bound={'expected_drawing_path':str(target),'expected_instance_hwnd':hwnd}
                result=await session.call_tool('draw_circle',dict(bound,cx=20,cy=20,radius=7))
                report['circle_mcp']=result.model_dump(mode='json')
                assert not result.isError and result.structuredContent['success'],result
                bad=await session.call_tool('draw_circle',dict(bound,expected_drawing_path=str(out/'wrong.dwg'),cx=0,cy=0,radius=1))
                report['wrong_target_mcp']=bad.model_dump(mode='json')
                assert bad.isError and bad.structuredContent['submitted'] is False
                result=await session.call_tool('get_active_drawing',bound)
                report['read_after_rejection']=result.model_dump(mode='json')
                assert not result.isError and result.structuredContent['success']
                return report['circle_mcp']['structuredContent']['handle']
    circle=asyncio.run(exercise())
    with exclusive('reliability-long-expression-save-test-only'):
        guard()
        conn=get_connection()
        conn._bound_document=str(target)
        conn._bound_hwnd=hwnd
        expr="(progn (length '("+' '.join(['1']*2500)+')) (cdr (assoc 5 (entget (entmakex (list (cons 0 "TEXT") (cons 10 (list 5.0 35.0 0.0)) (cons 40 3.0) (cons 1 "LONG BRIDGE TEST")))))))'
        report['expression_bytes']=len(expr.encode())
        text_handle=evaluate(conn,expr,timeout=15)
        report['text_handle']=text_handle
        guard()
        def verify(d):
            c=read_call(lambda:d.HandleToObject(circle))
            t=read_call(lambda:d.HandleToObject(text_handle))
            assert read_call(lambda:c.Radius)==7
            assert list(read_call(lambda:c.Center))==[20,20,0]
            assert read_call(lambda:t.TextString)=='LONG BRIDGE TEST'
            assert read_call(lambda:d.ModelSpace.Count)==2
            return {'entities':2,'circle_radius':7,'text':'LONG BRIDGE TEST'}
        report['before_reopen']=verify(doc)
        doc.Save()
        guard()
        doc.Close(False)
        doc=lookup_document_open(app)(str(target))
        doc=wait_for_document(app,target)
        guard()
        report['after_reopen']=verify(doc)
        app.ZoomExtents()
    report['after']=fingerprint()
    assert report['before']==report['after'],'Protected file changed'
    assert bool(original.Saved)==report['original_saved']
    assert int(original.ModelSpace.Count)==report['original_count']
    report['status']='passed'
except BaseException as exc:
    report.update(status='failed',error=repr(exc),after=fingerprint())
    raise
finally:
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps({'status':report['status'],'report':str(out/'report.json')},ensure_ascii=False))
    pythoncom.CoUninitialize()
