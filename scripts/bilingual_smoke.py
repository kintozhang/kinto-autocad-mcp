"""Create and validate a bilingual synthetic project and blank DWG seed."""
import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate, literal
from src.autocad.project_plot import ready, method, digest
from src.autocad.bilingual_titleblock import install
from scripts.verify_contact_terminal import validate

ROOT=Path(__file__).resolve().parents[1]


def circuit(doc):
    result={}
    for e in doc.ModelSpace:
        if e.ObjectName=='AcDbBlockReference' and e.Name.lower() not in {'din_tblock_a3','kinto_tb_a3_zh_en'}:
            result[e.Handle]={'block':e.Name,'attributes':{a.TagString:a.TextString for a in e.GetAttributes()} if e.HasAttributes else {}}
        elif e.ObjectName=='AcDbLine':
            result[e.Handle]={'layer':e.Layer,'start':list(e.StartPoint),'end':list(e.EndPoint)}
    return result


def main():
    assert '--write' in sys.argv
    source=ROOT/'work/projects/contact-terminal-20260924-190524'
    resume='--resume' in sys.argv
    folder=Path(sys.argv[sys.argv.index('--resume')+1]).resolve() if resume else ROOT/'work/projects'/datetime.now().strftime('bilingual-%Y%m%d-%H%M%S')
    if not resume:folder.mkdir()
    wdp=folder/(folder.name+'.wdp'); data=(source/'CONTACT-TERMINAL.wdp').read_text(encoding='utf8')
    pages=[]; originals={}
    for name in ['01-SUPPLY.dwg','02-CONTROL.dwg','03-CONTACT.dwg']:
        page=folder/(folder.name+'-'+name)
        if not resume:shutil.copy2(source/name,page)
        originals[str(source/name)]=digest(source/name)
        data=data.replace(name,page.name);pages.append(page)
    if not resume:wdp.write_text(data,encoding='utf8')
    if resume:
        shutil.copy2(folder/'acceptance.json',folder/('interrupted-'+datetime.now().strftime('%H%M%S')+'.json'))
        report=json.loads((folder/'acceptance.json').read_text(encoding='utf8'))
        assert len(report['pages'])==3 and all(p.get('save_reopen')=='PASS' for p in report['pages'])
        report.update(status='RESUMING_AFTER_SEED_FAILURE',recovery_note='Three pages already passed; no repeated title block writes')
    else:
        report={'status':'RUNNING','project':str(wdp),'pages':[],'calls':[]}
    def record():(folder/'acceptance.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    record();conn=get_connection();app=conn.get_application()
    titles=['供电 / Supply','控制 / Control','触点 / Contacts']
    def fields(index,title):
        return {'PROJECT':'控制样板 / Control demo','TITLE':title,'DRAWING_NO':f'KINTO-DEMO-{index:02d}',
                'SHEET':f'{index}/3','REV':'A','SCALE':'NTS','DRAWN_BY':'测试 / Test',
                'CHECKED_BY':'待审核 / Pending','DATE':'2026-09-24','STATUS':'样板 / TEST'}
    try:
        for index,page in ([] if resume else enumerate(pages,1)):
            doc=method(lambda:app.Documents.Open)(str(page));ready(doc)
            before=circuit(doc); values=fields(index,titles[index-1])
            item={'path':str(page),'titleblock':install(conn,page,values)};report['pages'].append(item);record()
            assert circuit(doc)==before
            doc.Regen(1);doc.Save();doc.Close(False)
            doc=method(lambda:app.Documents.Open)(str(page));ready(doc)
            assert circuit(doc)==before
            block=doc.HandleToObject(item['titleblock']['handle'])
            assert {a.TagString:a.TextString for a in block.GetAttributes()}==values
            item['save_reopen']='PASS';item['circuit_unchanged']='PASS';record()
        # Empty reusable DWG seed derived locally from the installed Electrical template.
        seed=folder/(('KINTO-A3-ZH-EN-SEED-'+datetime.now().strftime('%H%M%S')+'.dwg') if resume else 'KINTO-A3-ZH-EN-SEED.dwg')
        assert not seed.exists()
        template=Path(os.environ['LOCALAPPDATA'])/'Autodesk/AutoCAD Electrical 2026/R25.1/chs/Template/ACE_Din_a3_Color.dwt'
        shutil.copy2(template,seed)
        doc=method(lambda:app.Documents.Open)(str(seed));ready(doc);time.sleep(1)
        conn=get_connection()
        values=fields(1,'图名待填 / Title TBD');values['SHEET']='1/1';values['DRAWING_NO']='DRAWING-TBD'
        seed_result=install(conn,seed,values);doc.Regen(1);doc.Save();doc.Close(False)
        doc=method(lambda:app.Documents.Open)(str(seed));ready(doc);time.sleep(1)
        conn=get_connection()
        assert {a.TagString:a.TextString for a in doc.HandleToObject(seed_result['handle']).GetAttributes()}==values
        report['seed']={'path':str(seed),'attributes':values,'save_reopen':'PASS'};record()
        # Return to known project member and explicitly bind native project context.
        target=[app.Documents.Item(i) for i in range(app.Documents.Count) if Path(app.Documents.Item(i).FullName)==pages[-1]]
        assert len(target)==1;target[0].Activate()
        evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
        async def run():
            async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0'})) as (r,w):
                async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=120)) as s:
                    await s.initialize()
                    async def call(name,args):
                        response=await s.call_tool(name,args)
                        value=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
                        report['calls'].append({'tool':name,'result':value});record()
                        assert not response.isError and value['success'],value
                        return value
                    reports={}
                    for kind in ['bom','from_to','terminal_plan','terminal_numbers']:
                        reports[kind]=await call('export_electrical_project_report',{'project_path':str(wdp),'report_type':kind,'output_path':str(folder/(kind+'.csv'))})
                    validate(reports)
                    pdf=await call('export_electrical_project_pdf',{'project_path':str(wdp),'output_path':str(ROOT/'output/pdf/electrical-bilingual-20260924.pdf'),'template_mode':'synthetic_zh_en_a3'})
                    assert pdf['pages']==3
        asyncio.run(run())
        assert all(digest(p)==h for p,h in originals.items())
        report.update(status='STRUCTURE_AND_ELECTRICAL_PASS',visual_review='PENDING',originals_unchanged=True)
    except Exception as exc:
        report.update(status='FAILED',error=str(exc));raise
    finally:
        record();print(folder,flush=True)


if __name__=='__main__':main()
