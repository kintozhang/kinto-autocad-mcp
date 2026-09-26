"""Opt-in live gate acceptance: rejected MCP write, then one verified circle."""
import asyncio,json,os,shutil,sys
from datetime import datetime,timedelta
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.com_runtime import read_call,wait_for_document
from src.autocad.client_gate import exclusive
ROOT=Path(__file__).resolve().parents[1]

def main():
 assert '--write' in sys.argv
 folder=ROOT/'work/acceptance'/datetime.now().strftime('client-gate-%Y%m%d-%H%M%S');folder.mkdir()
 path=folder/(folder.name+'.dwg')
 report={'status':'RUNNING'}
 try:
  shutil.copy2(ROOT/'work/projects/bilingual-20260924-221032/KINTO-A3-ZH-EN-SEED-221509.dwg',path)
  app=get_connection().get_application()
  doc=read_call(lambda:app.Documents.Open)(str(path));doc=wait_for_document(app,path)
  before=read_call(lambda:doc.ModelSpace.Count)
  async def run():
   async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
    async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=60)) as s:
     await s.initialize()
     async def circle():
      res=await s.call_tool('draw_circle',{'cx':40.,'cy':100.,'radius':2.,'drawing_path':str(path)})
      return res.structuredContent or json.loads(next(x.text for x in res.content if x.type=='text'))
     with exclusive('acceptance-holder'):
      result=await circle()
      assert result['status']=='cad_in_use' and result['submitted'] is False,result
      assert read_call(lambda:doc.ModelSpace.Count)==before
      report['rejected']=result
     for expected in ({'expected_drawing_path':str(folder/'not-active.dwg')}, {'expected_instance_hwnd':1}):
      response=await s.call_tool('draw_circle',{'cx':40.,'cy':100.,'radius':2.,**expected})
      value=response.structuredContent
      assert value['status']=='target_rejected' and value['submitted'] is False,value
      assert read_call(lambda:doc.ModelSpace.Count)==before
      report.setdefault('target_rejections',[]).append(value)
     wait_for_document(app,path)
     result=await circle();report['accepted']=result
     assert result['success'],result
  asyncio.run(run())
  assert read_call(lambda:doc.ModelSpace.Count)==before+1
  obj=read_call(lambda:doc.ModelSpace.Item(before));handle=read_call(lambda:obj.Handle)
  assert read_call(lambda:obj.ObjectName)=='AcDbCircle'
  assert read_call(lambda:obj.Radius)==2.
  doc.Save();doc.Close(False)
  doc=read_call(lambda:app.Documents.Open)(str(path));wait_for_document(app,path)
  assert read_call(lambda:doc.ModelSpace.Count)==before+1
  obj=read_call(lambda:doc.HandleToObject(handle))
  assert read_call(lambda:obj.Radius)==2.
  assert tuple(read_call(lambda:obj.Center))==(40.,100.,0.)
  report.update(status='PASS',before=before,after=before+1,handle=handle,save_reopen='PASS')
 except Exception as exc:
  report.update(status='FAILED',error=str(exc));raise
 finally:
  (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print(folder,flush=True)
if __name__=='__main__':main()
