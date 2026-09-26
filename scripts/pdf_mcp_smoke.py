"""Explicit synthetic MCP PDF acceptance; no production project changes."""
import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate, literal
from src.autocad.project_plot import method, ready

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert '--write' in sys.argv
    source = ROOT/'work/projects/contact-terminal-20260924-190524'
    folder = ROOT/'work/projects'/datetime.now().strftime('pdf-mcp-%Y%m%d-%H%M%S')
    folder.mkdir()
    wdp = folder/(folder.name+'.wdp')
    data = (source/'CONTACT-TERMINAL.wdp').read_text(encoding='utf8')
    pages = []
    for name in ['01-SUPPLY.dwg','02-CONTROL.dwg','03-CONTACT.dwg']:
        page = folder/(folder.name+'-'+name)
        shutil.copy2(source/name,page); data=data.replace(name,page.name); pages.append(page)
    wdp.write_text(data,encoding='utf8')
    conn=get_connection(); app=conn.get_application(); docs=[]
    for page in pages:
        d=method(lambda:app.Documents.Open)(str(page)); ready(d)
        assert Path(d.FullName)==page
        d.Save(); docs.append(d)
    evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
    output=ROOT/'output/pdf/electrical-mcp-three-page-20260924.pdf' if '--default' in sys.argv else folder/'mcp-three-pages.pdf'
    log={'project':str(wdp),'output':str(output),'calls':[]}
    async def run():
        async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','src.server'],cwd=str(ROOT),env={**os.environ,'KINTO_MCP_EXPERIMENTAL':'0' if '--default' in sys.argv else '1'})) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=120)) as session:
                await session.initialize()
                names=[t.name for t in (await session.list_tools()).tools]
                assert 'export_electrical_project_pdf' in names
                log['registered_tools']=len(names)
                async def call(args, expected, name="export_electrical_project_pdf"):
                    response=await session.call_tool(name,args)
                    result=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=='text'))
                    log['calls'].append(result)
                    (folder/'mcp-acceptance.json').write_text(json.dumps(log,indent=2),encoding='utf8')
                    assert not response.isError and result['success']==expected,result
                    return result
                args={'project_path':str(source/'CONTACT-TERMINAL.wdp'),'output_path':str(output),'template_mode':'synthetic_din_a3'}
                await call(args,False)
                args['project_path']=str(wdp)
                result=await call(args,True)
                assert result['pages']==3 and result['active_drawing_restored']
                await call(args,False)
                # Independently reopen source fixture; confirm electrical meaning and reports.
                for page, doc in zip(pages, docs):
                    assert Path(doc.FullName)==page
                    doc.Close(False)
                for page in pages:
                    d=method(lambda:app.Documents.Open)(str(page)); ready(d)
                evaluate(get_connection(),'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
                wire=await call({'wire_handle':'9BE'},True,'get_electrical_wire')
                assert wire['wire_number']=='202' and len(wire['connections'])==2
                reports={}
                for kind in ['bom','from_to','terminal_plan','terminal_numbers']:
                    reports[kind]=await call({'project_path':str(wdp),'report_type':kind,'output_path':str(folder/(kind+'.csv'))},True,'export_electrical_project_report')
                from scripts.verify_contact_terminal import validate
                validate(reports)
                log['reopened_wire_and_reports']='PASS'
                log['status']='PASS'; (folder/'mcp-acceptance.json').write_text(json.dumps(log,indent=2),encoding='utf8')
    try:asyncio.run(run())
    finally:print(folder,flush=True)


if __name__=='__main__':main()
