"""Opt-in native MCP rebuild on a fresh copy of the accepted synthetic fixture."""
import asyncio,json,os,shutil,sys,time
from datetime import datetime,timedelta
from pathlib import Path
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate,literal
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]

def method(read):
    for attempt in range(10):
        try:return read()
        except AttributeError:
            if attempt==9:raise
            time.sleep(.3)

def main():
    assert "--write" in sys.argv
    source=ROOT/"work/projects/contact-terminal-20260924-190524"
    folder=ROOT/"work/projects"/datetime.now().strftime("contact-mcp-%Y%m%d-%H%M%S");folder.mkdir()
    for name in ["CONTACT-TERMINAL.wdp","01-SUPPLY.dwg","02-CONTROL.dwg","03-CONTACT.dwg"]:
        shutil.copy2(source/name,folder/name)
    wdp=folder/(folder.name+".wdp");(folder/"CONTACT-TERMINAL.wdp").rename(wdp);out=folder/"verification";out.mkdir()
    names=["01-SUPPLY.dwg","02-CONTROL.dwg","03-CONTACT.dwg"]
    new_names=[n.replace(".dwg", "-"+folder.name+".dwg") for n in names]
    data=wdp.read_text(encoding="utf8")
    for old,new in zip(names,new_names):
        (folder/old).rename(folder/new);data=data.replace(old,new)
    wdp.write_text(data,encoding="utf8")
    c=get_connection();app=c.get_application();docs=[];log=[]
    for name in new_names:
        d=method(lambda:app.Documents.Open)(str(folder/name));time.sleep(.3);docs.append(d)
        for attempt in range(20):
            try:
                if int(d.GetVariable("CMDACTIVE")) == 0:break
            except Exception:
                if attempt==19:raise
            time.sleep(.25)
        assert Path(d.FullName)==folder/name
        if name.startswith("02-CONTROL"):

            evaluate(c,'(c:wd_modattrval (handent "931") "XREFNO" "" nil)')
        if name.startswith("03-CONTACT"):

            evaluate(c,'(c:wd_modattrval (handent "8B3") "XREF" "" nil)')
            for h in ["9BE","9C0"]:d.HandleToObject(h).Delete()
        d.Save()
    try:evaluate(c,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
    except Exception as exc:log.append({"activation_observation":str(exc)})
    c=get_connection();assert Path(evaluate(c,"(ace_getactiveproject)"))==wdp
    async def run():
        async with stdio_client(StdioServerParameters(command=sys.executable,args=["-m","src.server"],cwd=str(ROOT),env={**os.environ,"KINTO_MCP_EXPERIMENTAL":"1"})) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=60)) as session:
                await session.initialize()
                async def call(name,args,success=True):
                    response=await session.call_tool(name,args)
                    data=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                    log.append({"tool":name,"args":args,"result":data});(out/"calls.json").write_text(json.dumps(log,indent=2),encoding="utf8")
                    assert not response.isError and data.get("success")==success,data
                    return data
                await call("update_electrical_cross_references",{"project_path":str(source/"CONTACT-TERMINAL.wdp")},False)
                wire=await call("connect_electrical_terminals",{"from_handle":"8B3","from_connection":"X1TERM02","to_handle":"965","to_connection":"X4TERM01"})
                assert len(wire["wire_handles"])==1,wire
                handle=wire["wire_handles"][0]
                await call("set_electrical_wire_number",{"wire_handle":handle,"number":"202"})
                await call("update_electrical_cross_references",{"project_path":str(wdp)},False) # unsaved guard
                docs[-1].Save()
                updated=await call("update_electrical_cross_references",{"project_path":str(wdp)})
                pair=updated["pairs"][0]
                assert pair["parent"]["attributes"]["XREFNO"]=="3.3-C"
                assert pair["child"]["attributes"]["XREF"]=="2.4-B"
                for d in docs:d.Save()
                # Reopen before report export and native wire readback.
                for d in docs:d.Close(False)
                for name in new_names:
                    method(lambda:app.Documents.Open)(str(folder/name));time.sleep(.3)
                # Electrical project globals are drawing-scoped; rebind after reopening.
                evaluate(get_connection(), '(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
                check=await call("get_electrical_wire",{"wire_handle":handle})
                assert check["wire_number"]=="202" and len(check["connections"])==2
                reports={}
                for kind in ["bom","from_to","terminal_plan","terminal_numbers"]:
                    reports[kind]=await call("export_electrical_project_report",{"project_path":str(wdp),"report_type":kind,"output_path":str(out/(kind+".csv"))})
                (out/"results.json").write_text(json.dumps(reports,indent=2),encoding="utf8")
                from scripts.verify_contact_terminal import validate
                validate(reports)
                (out/"smoke.json").write_text(json.dumps({"status":"PASS","wire_handle":handle,"save_reopen":"PASS","reports":"PASS","xref_operation":updated["operation_id"]},indent=2),encoding="utf8")
    try:asyncio.run(run())
    finally:print(folder,flush=True)

if __name__=="__main__":main()
