"""Independent saved-drawing verification, with no component or reference repair."""
import asyncio,json,os,sys
from datetime import timedelta,datetime
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.client_gate import exclusive
from src.autocad.com_runtime import lookup_document_open,wait_for_document
from src.autocad.lisp_bridge import evaluate,literal
from src.autocad.utils import get_block_attributes
from scripts.verify_pdf_project import lookup_saved_close
ROOT=Path(__file__).resolve().parents[1]

def main():
 folder=Path(sys.argv[1]).resolve();build=json.loads((folder/'acceptance.json').read_text(encoding='utf8'))
 paths=list(map(Path,build['drawings']));wdp=Path(build['project'])
 assert wdp.parent==folder and len(paths)==2 and all(p.parent==folder for p in paths)
 if not build.get('references'):
  build['references']=json.loads((folder/'reference-readback.json').read_text(encoding='utf8'))
 assert set(build['references'])=={'source','destination','parent','child'}
 out=folder/('reverification-'+datetime.now().strftime('%H%M%S'));out.mkdir()
 report={'status':'RUNNING','project':str(wdp),'calls':[],'references':{}}
 def record():(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 c=get_connection();app=c.get_application()
 try:
  with exclusive('trebi-independent-reopen'):
   found={Path(d.FullName).resolve() for d in app.Documents if d.FullName}
   for path in paths:
    if path in found:lookup_saved_close(app,path)(False)
   for path in paths:
    lookup_document_open(app)(str(path));doc=wait_for_document(app,path)
    for key,item in build['entities'].items():
     if Path(item['drawing'])==path and key in build['references']:
      actual=get_block_attributes(doc.HandleToObject(item['handle']))
      assert actual==build['references'][key],(key,actual)
      report['references'][key]=actual
    wd=next(e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference' and e.Name=='WD_M')
    data=get_block_attributes(wd);sheet=data['SHEET']
    if build.get('titles'):
     title=next(e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference' and e.Name=='KINTO_TREBI_ELECTRICAL_A3')
     assert get_block_attributes(title)==build['titles'][sheet]['after']
     report.setdefault('titles',{})[sheet]=get_block_attributes(title)
    assert all(data[k]==v for k,v in build['settings'][sheet]['settings'].items())
   assert report['references']['source']['XREF']=='112.8'
   assert report['references']['destination']['XREF']=='54.2'
   assert report['references']['child']['XREF']=='112.8'
   assert report['references']['parent']['XREFNO']=='54.5'
   report['save_reopen']='PASS';record()
   evaluate(c,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
  async def run():
   async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
    async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=120)) as s:
     await s.initialize()
     async def call(name,args):
      response=await s.call_tool(name,{**args,'expected_drawing_path':str(paths[-1])})
      result=response.structuredContent or json.loads(next(x.text for x in response.content if x.type=='text'))
      report['calls'].append({'tool':name,'result':result});record()
      assert not response.isError and result['success'],result
      return result
     wire=await call('get_electrical_wire',{'wire_handle':build['destination_wire']['wire_handles'][0]})
     assert wire['wire_number']=='501'
     reports={}
     for kind in ['bom','from_to','terminal_plan','terminal_numbers']:
      reports[kind]=await call('export_electrical_project_report',{'project_path':str(wdp),'report_type':kind,'output_path':str(out/(kind+'.csv'))})
     report['reports']=reports;record()
     assert {x[3]:int(x[1]) for x in reports['bom']['rows']}=={'RELAY_DEMO':1,'TERMINAL_DEMO':2}
     relay=next(x for x in reports['bom']['rows'] if x[3]=='RELAY_DEMO')
     assert relay[15]=='-112K1' and relay[25]=='112',relay
     rows=reports['from_to']['rows'];assert len(rows)==1 and rows[0][0]=='501',rows
     assert {(rows[0][2],rows[0][3]),(rows[0][5],rows[0][6])}=={('-X54','1'),('-X112','1')},rows
     assert {rows[0][11],rows[0][12]}=={'54','112'},rows
     assert {(x[0],x[1],x[2]) for x in reports['terminal_numbers']['rows']}=={('-X54','1','501'),('-X112','1','501')}
     plan=reports['terminal_plan']['rows'];assert len(plan)==2
     assert {(x[10],x[12],x[26]) for x in plan}=={('-X54','1','54'),('-X112','1','112')}
     assert all('501' in (x[8],x[17]) for x in plan)
  asyncio.run(run());report['status']='PASS'
 except Exception as exc:report.update(status='FAILED',error=repr(exc));raise
 finally:record();print(out,flush=True)
if __name__=='__main__':main()
