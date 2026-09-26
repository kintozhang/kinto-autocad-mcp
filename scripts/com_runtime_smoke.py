"""Opt-in live COM lifecycle acceptance with synthetic copies, not production drawings."""
import asyncio,json,os,shutil,sys
from datetime import datetime,timedelta
from pathlib import Path
import pythoncom
import win32com.client
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.com_runtime import read_call,wait_for_document

ROOT=Path(__file__).resolve().parents[1]


def main():
 assert '--write' in sys.argv
 folder=ROOT/'work/acceptance'/datetime.now().strftime('com-runtime-%Y%m%d-%H%M%S');folder.mkdir()
 seed=ROOT/'work/projects/bilingual-20260924-221032/KINTO-A3-ZH-EN-SEED-221509.dwg'
 paths=[folder/(folder.name+'-'+str(i)+'.dwg') for i in (1,2)]
 report={'status':'RUNNING','read_recoveries':[],'switches':[]}
 def record():(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 c=get_connection();app=c.get_application();docs=[]
 def read(f,label):return read_call(f,label=label,events=report['read_recoveries'])
 try:
  for path in paths:
   shutil.copy2(seed,path)
   doc=read(lambda:app.Documents.Open,'Open lookup')(str(path));wait_for_document(app,path);docs.append(doc)
  for index in range(20):
   which=index%2;docs[which].Activate();doc=wait_for_document(app,paths[which])
   assert c.is_connected() and c.get_application() is app
   info=read(lambda:(doc.FullName,doc.ModelSpace.Count,doc.TextStyles.Item('KINTO_ZH_EN').GetFont()[0]),'document snapshot')
   assert Path(info[0])==paths[which]
   report['switches'].append({'target':str(paths[which]),'entities':info[1],'font':info[2]});record()
  doc=wait_for_document(app,paths[1]);ms=read(lambda:doc.ModelSpace,'ModelSpace lookup')
  before=read(lambda:ms.Count,'entity count')
  point=win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,(40.,100.,0.))
  entity=read(lambda:ms.AddCircle,'AddCircle lookup')(point,2.)  # Exactly one write.
  handle=read(lambda:entity.Handle,'new circle handle')
  assert read(lambda:ms.Count,'entity count')==before+1
  doc.Save();doc.Close(False)
  doc=read(lambda:app.Documents.Open,'reopen lookup')(str(paths[1]));wait_for_document(app,paths[1])
  obj=read(lambda:doc.HandleToObject(handle),'circle readback')
  assert read(lambda:obj.Radius,'radius')==2.
  assert read(lambda:doc.ModelSpace.Count,'reopened count')==before+1
  report.update(circle={'handle':handle,'radius':2.,'created_count':1,'save_reopen':'PASS'})
  async def mcp():
   async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
    async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=60)) as s:
     await s.initialize();report['default_tools']=len((await s.list_tools()).tools)
     for name in ['get_active_drawing','list_drawings']:
      response=await s.call_tool(name,{})
      value=response.structuredContent or json.loads(next(x.text for x in response.content if x.type=='text'))
      assert not response.isError and value['success'],value
     report['default_mcp']='PASS'
  asyncio.run(mcp());report['status']='PASS'
 except Exception as exc:
  report.update(status='FAILED',error=str(exc));raise
 finally:record();print(folder,flush=True)


if __name__=='__main__':main()
