"""New synthetic NO/NC contact project and offset routing, through default MCP."""
import asyncio,json,os,shutil,sys,time
from datetime import datetime,timedelta
from pathlib import Path
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate,literal
from src.tools.native_cross_references import snapshot,pairs
from src.tools.native_project import guard
from scripts.contact_mcp_smoke import method
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
LIB=Path("C:/Users/Public/Documents/Autodesk/Acade 2026/Libs/iec2")

def ready(doc):
    for attempt in range(30):
        try:
            if int(doc.GetVariable("CMDACTIVE"))==0:return
        except Exception:
            if attempt==29:raise
        time.sleep(.25)
    raise RuntimeError("CAD did not become idle; no write attempted")

def validate_reports(reports):
    assert len(reports["bom"]["rows"])==4
    assert {r[3]:int(r[1]) for r in reports["bom"]["rows"]}=={"RELAY_DEMO":1,"FUSE_DEMO":1,"PUSHBUTTON_DEMO":1,"TERMINAL_DEMO":6}
    expected={("100","-X1","1","-F1","1"),("101","-F1","2","-S1","13"),("102","-X1","2","-K1","A2"),("103","-S1","14","-K1","A1"),("201","-X2","1","-K1","13"),("202","-K1","14","-X2","2"),("301","-X3","1","-K1","21"),("302","-K1","22","-X3","2")}
    # Native sorting may reverse a connection; preserve number and unordered endpoints.
    normalize=lambda v:(v[0],frozenset([(v[1],v[2]),(v[3],v[4])]))
    actual=[(r[0],r[2],r[3],r[5],r[6]) for r in reports["from_to"]["rows"]]
    assert len(actual)==8 and {normalize(r) for r in actual}=={normalize(r) for r in expected},actual
    terms={("-X1","1","100"),("-X1","2","102"),("-X2","1","201"),("-X2","2","202"),("-X3","1","301"),("-X3","2","302")}
    assert len(reports["terminal_numbers"]["rows"])==6
    assert {(r[0],r[1],r[2]) for r in reports["terminal_numbers"]["rows"]}==terms
    plan=reports["terminal_plan"]["rows"]
    assert len(plan)==6,plan
    assert {(r[10],r[12],r[8] or r[17]) for r in plan}==terms
    assert {(r[10],r[12],r[2] or r[23],r[3] or r[22]) for r in plan}=={("-X1","1","-F1","1"),("-X1","2","-K1","A2"),("-X2","1","-K1","13"),("-X2","2","-K1","14"),("-X3","1","-K1","21"),("-X3","2","-K1","22")}

def main():
    assert "--write" in sys.argv
    source=ROOT/"work/projects/contact-terminal-20260924-190524"
    folder=ROOT/"work/projects"/datetime.now().strftime("multicontact-%Y%m%d-%H%M%S");folder.mkdir()
    names=["01-SUPPLY.dwg","02-CONTROL.dwg","03-CONTACT.dwg"]
    pages=[folder/n.replace(".dwg","-"+folder.name+".dwg") for n in names]
    wdp=folder/(folder.name+".wdp");data=(source/"CONTACT-TERMINAL.wdp").read_text(encoding="utf8")
    for name,page in zip(names,pages):shutil.copy2(source/name,page);data=data.replace(name,page.name)
    wdp.write_text(data,encoding="utf8")
    out=folder/"verification";out.mkdir();report={"status":"RUNNING","project":str(wdp),"pages":[str(p) for p in pages],"calls":[]}
    def record():(out/"run.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    record();c=get_connection();app=c.get_application();docs=[]
    try:
        for page in pages:
            d=method(lambda:app.Documents.Open)(str(page));ready(d);assert Path(d.FullName)==page;docs.append(d)
        evaluate(c,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
        assert Path(evaluate(c,"(ace_getactiveproject)"))==wdp
        async def run():
            async with stdio_client(StdioServerParameters(command=sys.executable,args=["-m","src.server"],cwd=str(ROOT),env={**os.environ,"KINTO_MCP_EXPERIMENTAL":"0"})) as (r,w):
                async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=60)) as s:
                    await s.initialize()
                    async def call(name,args):
                        assert Path(app.ActiveDocument.FullName).parent==folder
                        response=await s.call_tool(name,args)
                        value=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                        report["calls"].append({"tool":name,"args":args,"result":value});record()
                        assert not response.isError and value.get("success"),value
                        return value
                    nc=await call("insert_electrical_symbol",{"symbol_name":str(LIB/"HCR22.dwg"),"x":140,"y":110,"attributes":{"TAG2":"-K1","TERM01":"21","TERM02":"22"}})
                    assert nc["attributes"]["CONTACT"]=="NC",nc
                    terminals=[]
                    for number,x,y in [("1",70,130),("2",210,90)]:
                        terminals.append(await call("insert_electrical_symbol",{"symbol_name":str(LIB/"HT0001.dwg"),"x":x,"y":y,"attributes":{"TAGSTRIP":"X3","TERM01":number,"MFG":"KINTO_TEST","CAT":"TERMINAL_DEMO"}}))
                    nets=[]
                    for f,fp,t,tp,number in [(terminals[0]["handle"],"X1TERM01",nc["handle"],"X4TERM01","301"),(nc["handle"],"X1TERM02",terminals[1]["handle"],"X4TERM01","302")]:
                        wire=await call("connect_electrical_terminals",{"from_handle":f,"from_connection":fp,"to_handle":t,"to_connection":tp})
                        await call("set_electrical_wire_number",{"wire_handle":wire["wire_handles"][0],"number":number})
                        nets.append({"handles":wire["wire_handles"],"number":number,"expected":[[f,fp],[t,tp]]})
                    docs[-1].Save()
                    ref=await call("update_electrical_cross_references",{"project_path":str(wdp)})
                    assert len(ref["pairs"])==2
                    for pair in ref["pairs"]:
                        assert pair["child"]["attributes"]["XREF"]=="2.4-B"
                        expected="3.3-C" if pair["child"]["attributes"]["CONTACT"]=="NO" else "%%u3.3-D%%u"
                        assert pair["parent"]["attributes"][pair["parent_reference_field"]]==expected,pair
                    for d in docs:d.Save()
                    for d in docs:d.Close(False)
                    for page in pages:
                        d=method(lambda:app.Documents.Open)(str(page));ready(d)
                    evaluate(get_connection(),'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
                    for net in nets:
                        for h in net["handles"]:
                            wire=await call("get_electrical_wire",{"wire_handle":h})
                            assert wire["wire_number"]==net["number"]
                            assert {tuple(p) for p in wire["connections"]}=={tuple(p) for p in net["expected"]},wire
                            a,b=wire["start"],wire["end"];assert a!=b and (a[0]==b[0] or a[1]==b[1]),wire
                    after=pairs(snapshot(get_connection(),guard(get_connection(),str(wdp)),False),True)
                    assert after==ref["pairs"],after
                    report["reopened_pairs"]=after;report["nets"]=nets
                    reports={}
                    for kind in ["bom","from_to","terminal_plan","terminal_numbers"]:
                        reports[kind]=await call("export_electrical_project_report",{"project_path":str(wdp),"report_type":kind,"output_path":str(out/(kind+".csv"))})
                    report["reports"]=reports;record();validate_reports(reports)
                    report["save_reopen"]="PASS"
        asyncio.run(run());report["status"]="PASS"
    except BaseException as exc:report["status"]="FAIL";report["error"]=repr(exc);raise
    finally:record();print(folder,flush=True)

if __name__=="__main__":main()
