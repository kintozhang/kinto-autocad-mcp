"""Independent save/reopen and native-report verification after PDF generation."""
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate, literal
from src.autocad.project_plot import project_pages, method, ready
from scripts.verify_contact_terminal import validate

ROOT=Path(__file__).resolve().parents[1]


def lookup_saved_close(app, page, attempts=8):
    """Retry only fresh read-only lookup; caller invokes returned Close once."""
    from src.autocad.com_runtime import read_call
    page=Path(page).resolve()
    def lookup():
        for i in range(app.Documents.Count):
            doc=app.Documents.Item(i)
            if Path(doc.FullName).resolve()==page:
                if not doc.Saved:
                    raise ValueError("Refusing to close an unsaved verification drawing")
                return doc.Close
        raise ValueError("Verification drawing no longer open")
    for attempt in range(attempts):
        try:
            return read_call(lookup,label="saved Close method lookup")
        except AttributeError:
            if attempt+1==attempts:raise
            time.sleep(.15)


def main():
    folder=Path(sys.argv[1]).resolve(); wdp=folder/(folder.name+'.wdp'); pages=project_pages(wdp)
    from datetime import datetime
    out=folder/('independent-reverification-'+datetime.now().strftime('%H%M%S') if '--fresh' in sys.argv else 'independent-reverification'); out.mkdir(exist_ok=False)
    conn=get_connection(); app=conn.get_application()
    # Read-only enumeration retry. Never retry Close/Open or any CAD write.
    for attempt in range(10):
        try:
            docs=[app.Documents.Item(i) for i in range(app.Documents.Count)]
            found={Path(d.FullName).resolve():d for d in docs if Path(d.FullName).resolve() in pages}
            break
        except Exception:
            if attempt==9:raise
            time.sleep(.3)
    for page,doc in found.items():
        assert Path(doc.FullName).resolve()==page
        lookup_saved_close(app,page)(False)
    for page in pages:
        doc=method(lambda:app.Documents.Open)(str(page))
        from src.autocad.com_runtime import wait_for_document
        doc=wait_for_document(app,page)
        assert Path(doc.FullName)==page
    evaluate(get_connection(),'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
    async def run():
        async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=120)) as s:
                await s.initialize()
                report={'default_tools':len((await s.list_tools()).tools),'calls':[]}
                async def call(name,args):
                    response=await s.call_tool(name,args)
                    result=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
                    report['calls'].append({'tool':name,'result':result})
                    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
                    assert not response.isError and result['success'],result
                    return result
                wire=await call('get_electrical_wire',{'wire_handle':'9BE'})
                assert wire['wire_number']=='202' and len(wire['connections'])==2
                reports={}
                for kind in ['bom','from_to','terminal_plan','terminal_numbers']:
                    reports[kind]=await call('export_electrical_project_report',{'project_path':str(wdp),'report_type':kind,'output_path':str(out/(kind+'.csv'))})
                validate(reports)
                report.update(status='PASS',reopened_wire_and_reports='PASS')
                (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    asyncio.run(run()); print(out)


if __name__=='__main__':main()
