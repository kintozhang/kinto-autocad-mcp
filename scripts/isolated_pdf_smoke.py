"""Opt-in isolated MCP PDF acceptance on a fresh synthetic project."""
import asyncio,json,os,shutil,subprocess,sys
from datetime import datetime,timedelta
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.com_runtime import read_call,wait_for_document
from src.autocad.lisp_bridge import evaluate,literal
from src.autocad.project_plot import project_pages
ROOT=Path(__file__).resolve().parents[1]

def main():
 assert '--write' in sys.argv
 source=ROOT/'work/projects/title-mapping-20260924-224719'
 source_wdp=source/(source.name+'.wdp')
 folder=ROOT/'work/projects'/datetime.now().strftime('target-pdf-%Y%m%d-%H%M%S');folder.mkdir()
 wdp=folder/(folder.name+'.wdp');data=source_wdp.read_text(encoding='utf-8-sig')
 for i,page in enumerate(project_pages(source_wdp),1):
  name=folder.name+f'-{i:02d}.dwg';shutil.copy2(page,folder/name);data=data.replace(page.name,name)
 wdp.write_text(data,encoding='utf-8-sig')
 output=ROOT/'output/pdf'/(folder.name+'.pdf')
 report={'status':'RUNNING','project':str(wdp),'pdf':str(output)}
 try:
  conn=get_connection();app=conn.get_application()
  for path in project_pages(wdp):
   read_call(lambda:app.Documents.Open)(str(path));wait_for_document(app,path)
  evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
  original=read_call(lambda:app.ActiveDocument.FullName);hwnd=read_call(lambda:int(app.HWND))
  async def run():
   async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
    async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=240)) as s:
     await s.initialize()
     response=await s.call_tool('export_electrical_project_pdf',{'project_path':str(wdp),'output_path':str(output),'template_mode':'synthetic_zh_en_a3','expected_drawing_path':original,'expected_instance_hwnd':hwnd})
     result=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
     report['export']=result
     assert not response.isError and result['success'],result
     assert result['source_files_unchanged'] and result['active_drawing_restored']
     diag=(await s.call_tool('get_execution_diagnostics',{})).structuredContent
     assert diag['marker'] is None and not diag['cad_contacted']
     report['diagnostics']=diag
  asyncio.run(run())
  subprocess.run([sys.executable,'-m','scripts.verify_pdf_project',str(folder)],check=True)
  report['status']='STRUCTURE_AND_ELECTRICAL_PASS_VISUAL_PENDING'
 except Exception as exc:
  report.update(status='FAILED',error=str(exc));raise
 finally:
  (folder/'acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print(folder,flush=True)
if __name__=='__main__':main()
