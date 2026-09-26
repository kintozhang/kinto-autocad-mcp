"""Two-page native X-zone acceptance in fresh synthetic TREBI frames."""
import asyncio,json,os,shutil,sys
from datetime import datetime,timedelta
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.com_runtime import read_call,wait_for_document,lookup_document_open
from src.autocad.client_gate import exclusive
from src.autocad.lisp_bridge import evaluate,literal
from src.autocad.trebi_native_grid import configure
from src.autocad.trebi_component_tags import plan_tags
from src.autocad.trebi_project_pages import plan as plan_pages
from src.autocad.trebi_title_mapping import apply as apply_title
from src.autocad.utils import get_block_attributes
from scripts.verify_pdf_project import lookup_saved_close
ROOT=Path(__file__).resolve().parents[1]
LIB=Path('C:/Users/Public/Documents/Autodesk/Acade 2026/Libs/iec2')

def main():
 assert '--write' in sys.argv
 folder=ROOT/'work/projects'/datetime.now().strftime('trebi-zones-%Y%m%d-%H%M%S');folder.mkdir()
 wdp=folder/(folder.name+'.wdp');sheets=['54','112'];paths=[folder/(folder.name+'-'+s+'.dwg') for s in sheets]
 manifest={'schema_version':1,'entries':[{'id':sheet,'kind':'drawing','logical_page':sheet,'include_in_total':True,'drawing_file':path.name} for sheet,path in zip(sheets,paths)]}
 components=plan_tags(manifest,[{'id':'relay','role':'primary','family':'K','drawing_page':'112','owner_page':'112'},{'id':'contact','role':'child','drawing_page':'54','parent_id':'relay'}])
 tags={c['id']:c['tag'] for c in components['components']}
 shutil.copy2(ROOT/'profiles/trebi-electrical-a3.wdt',wdp.with_suffix('.wdt'))
 (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
 report={'manifest':manifest,'component_plan':components,'titles':{},'status':'RUNNING','project':str(wdp),'drawings':list(map(str,paths)),'settings':{},'entities':{},'calls':[]}
 def record():(folder/'acceptance.json').write_text(json.dumps(report,ensure_ascii=True,indent=2),encoding='utf8')
 conn=get_connection();app=conn.get_application();docs=[];target=None
 def activate(i):
  nonlocal target
  with exclusive('trebi-test-navigation'):
   docs[i].Activate();target=paths[i];wait_for_document(app,target)
   evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
 def attrs(key):
  item=report['entities'][key];return get_block_attributes(app.ActiveDocument.HandleToObject(item['handle']))
 try:
  with exclusive('trebi-grid-project-bootstrap'):
   expr='((lambda (/ p) (setq p (c:wd_proj_wdp_data)) (c:wd_proj_wdp_write '+literal(wdp.as_posix())+' '+literal(['','KINTO TREBI RULE TEST']+['']*18+[str(plan_pages(manifest)['effective_drawing_count'])])+' (nth 3 p) (nth 4 p) nil) T))'
   evaluate(conn,expr);evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
   for i,path in enumerate(paths):
    shutil.copy2(ROOT/'work/acceptance/trebi-frame-20260925-084127/KINTO-TREBI-ELECTRICAL-A3.dwg',path)
    lookup_document_open(app)(str(path));doc=wait_for_document(app,path);docs.append(doc)
    assert evaluate(conn,'(c:ace_add_dwg_to_project '+literal(path.as_posix())+' (list "" "" "SYNTHETIC X ZONE TEST" nil nil))')==1
    report['settings'][sheets[i]]=configure(conn,path,sheets[i]);record()
    title=next(e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference' and e.Name=='KINTO_TREBI_ELECTRICAL_A3')
    for a in title.GetAttributes():
     values={'PAGE':'999','OF':'999','PREV':'999','NEXT':'999','DESCRIPTION':'SYNTHETIC NATIVE X-ZONE TEST','PLAN':'KINTO-XZONE-TEST'}
     if a.TagString in values:a.TextString=values[a.TagString]
    doc.Save()
  for i,path in enumerate(paths):
   activate(i)
   with exclusive('trebi-native-title-mapping'):
    report['titles'][sheets[i]]=apply_title(conn,wdp,manifest,path);docs[i].Save();record()
  async def run():
   async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
    async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=120)) as session:
     await session.initialize()
     async def call(name,args):
      response=await session.call_tool(name,{**args,'expected_drawing_path':str(target)})
      result=response.structuredContent or json.loads(next(x.text for x in response.content if x.type=='text'))
      report['calls'].append({'tool':name,'drawing':str(target),'result':result});record()
      assert not response.isError and result['success'],result
      return result
     async def insert(key,symbol,x,y,attributes):
      result=await call('insert_electrical_symbol',{'symbol_name':str(LIB/(symbol+'.dwg')),'x':x,'y':y,'attributes':attributes})
      report['entities'][key]={'drawing':str(target),**result};record()
     async def link(a,ap,b,bp):
      return await call('connect_electrical_terminals',{'from_handle':report['entities'][a]['handle'],'from_connection':ap,'to_handle':report['entities'][b]['handle'],'to_connection':bp})
     activate(1)
     await insert('parent','HCR1',350,150,{'TAG1':tags['relay'],'TERM01':'A1','TERM02':'A2','MFG':'KINTO_TEST','CAT':'RELAY_DEMO','DESC1':'UNWIRED REFERENCE TEST'})
     await insert('destination','HA1D3',330,210,{'SIGCODE':'KINTO_TREBI_XZONE_TEST','DESC1':'TEST SOURCE AT 54.2'})
     await insert('terminal112','HT0001',390,210,{'TAGSTRIP':'X112','TERM01':'1','MFG':'KINTO_TEST','CAT':'TERMINAL_DEMO'})
     report['destination_wire']=await link('destination','X1TERM01','terminal112','X4TERM01');app.ActiveDocument.Save()
     activate(0)
     await insert('child','HCR21',230,150,{'TAG2':tags['contact'],'TERM01':'13','TERM02':'14','DESC1':'UNWIRED REFERENCE TEST'})
     await insert('terminal54','HT0001',70,210,{'TAGSTRIP':'X54','TERM01':'1','MFG':'KINTO_TEST','CAT':'TERMINAL_DEMO'})
     await insert('source','HA1S1',110,210,{'SIGCODE':'KINTO_TREBI_XZONE_TEST','DESC1':'TEST DESTINATION AT 112.8'})
     report['source_wire']=await link('terminal54','X1TERM01','source','X4TERM01')
     await call('set_electrical_wire_number',{'wire_handle':report['source_wire']['wire_handles'][0],'number':'501'});app.ActiveDocument.Save()
     for i in range(2):
      activate(i);await call('update_electrical_signals',{'project_path':str(wdp)});app.ActiveDocument.Save()
     await call('update_electrical_cross_references',{'project_path':str(wdp)})
     for i in range(2):
      activate(i);app.ActiveDocument.Save()
     report['references']={}
     for i,checks in [(0,{'source':('XREF','112.8'),'child':('XREF','112.8')}),(1,{'destination':('XREF','54.2'),'parent':('XREFNO','54.5')})]:
      activate(i)
      for key,(field,want) in checks.items():
       data=attrs(key);report['references'][key]=data;record();assert data[field]==want,(key,field,want,data)
     # Save/reopen, no reference repair during independent readback.
     for path in paths:lookup_saved_close(app,path)(False)
     docs.clear()
     for path in paths:
      lookup_document_open(app)(str(path));docs.append(wait_for_document(app,path))
     for i,keys in [(0,['source','child']),(1,['destination','parent'])]:
      activate(i)
      for key in keys:assert attrs(key)==report['references'][key]
      wd=next(e for e in app.ActiveDocument.ModelSpace if e.ObjectName=='AcDbBlockReference' and e.Name=='WD_M')
      data=get_block_attributes(wd)
      title=next(e for e in app.ActiveDocument.ModelSpace if e.ObjectName=='AcDbBlockReference' and e.Name=='KINTO_TREBI_ELECTRICAL_A3')
      assert get_block_attributes(title)==report['titles'][sheets[i]]['after']
      assert all(data[k]==v for k,v in report['settings'][sheets[i]]['settings'].items())
     report['save_reopen']='PASS'
     wire=await call('get_electrical_wire',{'wire_handle':report['destination_wire']['wire_handles'][0]})
     assert wire['wire_number']=='501',wire
     reports={}
     for kind in ['bom','from_to','terminal_plan','terminal_numbers']:
      reports[kind]=await call('export_electrical_project_report',{'project_path':str(wdp),'report_type':kind,'output_path':str(folder/(kind+'.csv'))})
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
 except Exception as exc:report.update(status='FAILED',error=str(exc));raise
 finally:record();print(folder,flush=True)
if __name__=='__main__':main()
