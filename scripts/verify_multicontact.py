"""Independent recovery verification; never repeat a failed CAD drawing write."""
import asyncio,json,os,sys
from datetime import datetime,timedelta
from pathlib import Path
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate,literal
from src.tools.native_cross_references import snapshot,pairs
from src.tools.native_project import guard
from scripts.contact_mcp_smoke import method
from scripts.multicontact_smoke import ready,validate_reports
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

def check_refs(rows):
    assert len(rows)==2
    for row in rows:
        a=row["child"]["attributes"];p=row["parent"]["attributes"]
        assert a["XREF"]=="2.4-B"
        assert p["XREFNO"]=="3.3-C" and p["XREFNC"]=="%%u3.3-D%%u"
        assert (a["CONTACT"],a["TERM01"],a["TERM02"]) in {("NO","13","14"),("NC","21","22")}

def main():
    folder=Path(sys.argv[1]).resolve();build=json.loads((folder/"verification/run.json").read_text(encoding="utf8"))
    wdp=Path(build["project"]);assert wdp.parent==folder
    pages=[Path(p) for p in build["pages"]];assert all(p.parent==folder for p in pages)
    out=folder/datetime.now().strftime("reverification-%H%M%S");out.mkdir();report={"status":"RUNNING","source_build_status":build["status"],"calls":[]}
    def record():(out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    c=get_connection();app=c.get_application();refs=pairs(snapshot(c,guard(c,str(wdp)),False),True);check_refs(refs)
    report["before"]=refs;record()
    # The failed call is not retried. Only verified fixture documents are saved.
    docs=[d for d in app.Documents if Path(d.FullName) in pages];assert len(docs)==3
    for d in docs:d.Save()
    for d in docs:d.Close(False)
    for page in pages:d=method(lambda:app.Documents.Open)(str(page));ready(d)
    evaluate(get_connection(),'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
    async def run():
        async with stdio_client(StdioServerParameters(command=sys.executable,args=["-m","src.server"],cwd=str(Path(__file__).resolve().parents[1]),env={**os.environ,"KINTO_MCP_EXPERIMENTAL":"0"})) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=60)) as s:
                await s.initialize()
                async def call(name,args):
                    response=await s.call_tool(name,args)
                    value=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                    report["calls"].append({"tool":name,"args":args,"result":value});record()
                    assert not response.isError and value.get("success"),value
                    return value
                connects=[i for i in build["calls"] if i["tool"]=="connect_electrical_terminals" and i["result"].get("success")]
                assert len(connects)==2
                for item,number in zip(connects,["301","302"]):
                    a=item["args"];expected={(a["from_handle"],a["from_connection"]),(a["to_handle"],a["to_connection"])}
                    for h in item["result"]["wire_handles"]:
                        wire=await call("get_electrical_wire",{"wire_handle":h})
                        assert wire["wire_number"]==number and {tuple(n) for n in wire["connections"]}==expected,wire
                        a,b=wire["start"],wire["end"];assert a!=b and (a[0]==b[0] or a[1]==b[1])
                after=pairs(snapshot(get_connection(),guard(get_connection(),str(wdp)),False),True);check_refs(after);assert after==refs
                report["after"]=after;reports={}
                for kind in ["bom","from_to","terminal_plan","terminal_numbers"]:
                    reports[kind]=await call("export_electrical_project_report",{"project_path":str(wdp),"report_type":kind,"output_path":str(out/(kind+".csv"))})
                report["reports"]=reports;record();validate_reports(reports)
    try:asyncio.run(run());report["status"]="PASS";report["save_reopen"]="PASS"
    except BaseException as exc:report["status"]="FAIL";report["error"]=repr(exc);raise
    finally:record();print(out,flush=True)

if __name__=="__main__":main()
