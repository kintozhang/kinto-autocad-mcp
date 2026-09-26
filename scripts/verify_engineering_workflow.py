"""Explicit acceptance on generated test projects only; keeps all user originals open."""
import argparse,asyncio,json,os,sys
from pathlib import Path
from datetime import timedelta
import pythoncom
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.client_gate import exclusive
from src.autocad.com_runtime import read_call,lookup_document_open,wait_for_document
from src.autocad.change_audit import snapshot
from src.autocad.lisp_bridge import evaluate,literal
ROOT=Path(__file__).resolve().parents[1]


async def run(args):
    pythoncom.CoInitialize();conn=get_connection();app=conn.get_application();hwnd=int(app.HWND)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    for input_path in [args.mechanical,args.electrical]:
        data=json.loads(Path(input_path).read_text());assert data['spec']['purpose']=='test_only'
        with exclusive('verify-generated-project-reopen'):
            for path in data['plan']['drawings']:
                target=Path(path);doc=next(d for d in app.Documents if Path(d.FullName)==target)
                assert read_call(lambda:bool(doc.Saved))
                before=read_call(lambda:snapshot(doc))
                read_call(lambda:doc.Close)(False)
                lookup_document_open(app)(str(target));doc=wait_for_document(app,target)
                assert read_call(lambda:snapshot(doc))==before
                (output/(target.stem+'-snapshot.json')).write_text(json.dumps(before,indent=2))
    async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
        async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=660)) as client:
            await client.initialize()
            async def call(label,name,values):
                response=await client.call_tool(name,values)
                result=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
                (output/(label+'.json')).write_text(json.dumps(result,indent=2))
                assert result['success'],result
                print(label,'passed',flush=True);return result
            recovered=await call('restore','restore_cad_project',{'archive_path':args.archive,'destination':str(output/'recovered'),'project_name':output.name+'-RECOVERED'})
            with exclusive('open-recovered-independent-project'):
                for path in recovered['drawings']:
                    lookup_document_open(app)(path);wait_for_document(app,path)
                evaluate(conn,'(progn (c:wd_makeproj_current '+literal(recovered['project_path'].replace('\\','/'))+') T)')
            target=recovered['drawings'][-1]
            for kind in ['bom','from_to','terminal_plan','terminal_numbers']:
                result=await call(kind,'export_electrical_project_report',{'project_path':recovered['project_path'],'report_type':kind,'output_path':str(output/(kind+'.csv')),'expected_drawing_path':target,'expected_instance_hwnd':hwnd})
                expected=json.loads((Path(args.reference)/('final-'+kind+'.json')).read_text())['rows']
                assert result['rows']==expected,kind
            audit=await call('audit','audit_cad_project',{'project_path':recovered['project_path'],'evidence_files':[]})
            assert not audit['formal_export_allowed'] and len(audit['blockers'])==10
    (output/'summary.json').write_text(json.dumps({'project_creation_reopen':True,'restored_native_reports_match':True,'missing_evidence_blocks':True,'production_ready':False},indent=2))


def main():
    p=argparse.ArgumentParser()
    for field in ['mechanical','electrical','archive','output','reference']:p.add_argument('--'+field,required=True)
    asyncio.run(run(p.parse_args()))

if __name__=='__main__':main()
