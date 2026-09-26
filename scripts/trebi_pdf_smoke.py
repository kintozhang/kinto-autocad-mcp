"""Default MCP export of an accepted TREBI batch without modifying source DWGs."""
import asyncio,json,os,sys
from pathlib import Path
from datetime import datetime,timedelta
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.com_runtime import read_call,wait_for_document
from src.autocad.client_gate import exclusive
from src.autocad.lisp_bridge import evaluate,literal
from src.autocad.project_plot import project_pages,digest
ROOT=Path(__file__).resolve().parents[1]

def main():
    assert '--write' in sys.argv
    folder=Path(sys.argv[1]).resolve();build=json.loads((folder/'acceptance.json').read_text(encoding='utf8'))
    wdp=Path(build['project']);pages=project_pages(wdp)
    out=ROOT/'output/pdf'/('trebi-batch-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.pdf');out.parent.mkdir(parents=True,exist_ok=True)
    record=folder/('pdf-acceptance-'+datetime.now().strftime('%H%M%S')+'.json')
    report={'status':'RUNNING','project':str(wdp),'output':str(out)}
    print(record,flush=True)
    try:
        conn=get_connection();app=conn.get_application()
        with exclusive('trebi-pdf-test-navigation'):
            docs={Path(d.FullName).resolve():d for d in app.Documents if d.FullName}
            assert all(p in docs and docs[p].Saved for p in pages)
            docs[pages[-1]].Activate();wait_for_document(app,pages[-1])
            evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
            hwnd=read_call(lambda:int(app.HWND))
        hashes={str(p):digest(p) for p in [wdp,*pages]}
        async def run():
            async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
                async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=240)) as session:
                    await session.initialize()
                    response=await session.call_tool('export_electrical_project_pdf',{'project_path':str(wdp),'output_path':str(out),'template_mode':'synthetic_trebi_a3','expected_drawing_path':str(pages[-1]),'expected_instance_hwnd':hwnd})
                    result=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
                    report['export']=result
                    assert not response.isError and result['success'],result
                    assert result['logical_page_order']==['54','112'] and result['source_files_unchanged'] and result['active_drawing_restored']
                    assert all(digest(p)==value for p,value in hashes.items())
                    report['source_sha256']=hashes
        asyncio.run(run());report['status']='STRUCTURE_PASS_VISUAL_AND_REOPEN_PENDING'
    except Exception as exc:report.update(status='FAILED',error=str(exc));raise
    finally:record.write_text(json.dumps(report,indent=2),encoding='utf8');print(out,flush=True)
if __name__=='__main__':main()
