"""Fresh two-page fixture through default MCP batch, then independent verifier."""
import asyncio,json,os,shutil,sys
from pathlib import Path
from datetime import datetime,timedelta
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.com_runtime import lookup_document_open,wait_for_document
from src.autocad.client_gate import exclusive
from src.autocad.lisp_bridge import evaluate,literal
ROOT=Path(__file__).resolve().parents[1]

def main():
    assert '--write' in sys.argv
    folder=ROOT/'work/projects'/datetime.now().strftime('trebi-batch-%Y%m%d-%H%M%S');folder.mkdir()
    spec=json.loads((ROOT/'examples/trebi-batch.json').read_text(encoding='utf8'))
    wdp=folder/(folder.name+'.wdp')
    paths=[]
    for entry in spec['manifest']['entries']:
        entry['drawing_file']=folder.name+'-'+entry['logical_page']+'.dwg'
        paths.append(folder/entry['drawing_file'])
    (folder/'spec.json').write_text(json.dumps(spec,indent=2),encoding='utf8')
    print(folder,flush=True)
    conn=get_connection();app=conn.get_application()
    with exclusive('trebi-batch-test-bootstrap'):
        shutil.copy2(ROOT/'profiles/trebi-electrical-a3.wdt',wdp.with_suffix('.wdt'))
        evaluate(conn,'((lambda (/ p) (setq p (c:wd_proj_wdp_data)) (c:wd_proj_wdp_write '+literal(wdp.as_posix())+' '+literal(['','KINTO TREBI BATCH TEST']+['']*18+['2'])+' (nth 3 p) (nth 4 p) nil) T))')
        evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
        for path in paths:
            shutil.copy2(ROOT/'work/acceptance/trebi-frame-20260925-084127/KINTO-TREBI-ELECTRICAL-A3.dwg',path)
            lookup_document_open(app)(str(path));doc=wait_for_document(app,path)
            assert evaluate(conn,'(c:ace_add_dwg_to_project '+literal(path.as_posix())+' (list "" "" "SYNTHETIC BATCH TEST" nil nil))')==1
            doc.Save()
        evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
    async def run():
        async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=660)) as session:
                await session.initialize()
                names={t.name for t in (await session.list_tools()).tools}
                assert {'plan_trebi_batch','execute_trebi_batch'}<=names
                for name,args in [('plan_trebi_batch',{'spec':spec}),('execute_trebi_batch',{'project_path':str(wdp),'spec':spec,'drawing_path':str(paths[-1]),'expected_drawing_path':str(paths[-1]),'expected_instance_hwnd':int(app.HWND)})]:
                    response=await session.call_tool(name,args)
                    result=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
                    (folder/(name+'.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
                    assert not response.isError and result['success'],result
                build={**result,'status':'BATCH_PASS_REOPEN_PENDING','references':{k:result['references'][k] for k in ['parent','child','source','destination']},**result['wires']}
                (folder/'acceptance.json').write_text(json.dumps(build,indent=2),encoding='utf8')
                # A second identical recipe must be refused before any new insert.
                response=await session.call_tool('execute_trebi_batch',{'project_path':str(wdp),'spec':spec,'drawing_path':str(paths[-1]),'expected_drawing_path':str(paths[-1])})
                rejected=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
                (folder/'replay-rejection.json').write_text(json.dumps(rejected,indent=2),encoding='utf8')
                assert rejected['status']=='preflight_rejected' and rejected['submitted'] is False,rejected
    asyncio.run(run())
    print('BATCH PASS; run scripts.verify_trebi_native_grid on this folder',flush=True)
if __name__=='__main__':main()
