"""Independent crossing-wire isolation acceptance through default stdio MCP."""
import asyncio,json,os,sys
from pathlib import Path
from datetime import datetime,timedelta
from src.autocad.connection import get_connection
from scripts.contact_mcp_smoke import method
from scripts.multicontact_smoke import ready,LIB
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]

def main():
    assert "--write" in sys.argv
    folder=ROOT/"work/acceptance"/datetime.now().strftime("branch-%Y%m%d-%H%M%S");folder.mkdir()
    path=folder/(folder.name+".dwg");report={"status":"RUNNING","drawing":str(path),"calls":[]}
    def record():(folder/"report.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    app=get_connection().get_application()
    d=method(lambda:app.Documents.Add)("C:/Users/James/AppData/Local/Autodesk/AutoCAD Electrical 2026/R25.1/chs/Template/ACE_Din_a3_Color.dwt")
    ready(d);d.SaveAs(str(path));ready(d)
    async def run():
        nonlocal d
        async with stdio_client(StdioServerParameters(command=sys.executable,args=["-m","src.server"],cwd=str(ROOT),env={**os.environ,"KINTO_MCP_EXPERIMENTAL":"1"})) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=60)) as s:
                await s.initialize()
                async def call(name,args):
                    assert Path(app.ActiveDocument.FullName)==path
                    response=await s.call_tool(name,args)
                    value=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                    report["calls"].append({"tool":name,"args":args,"result":value});record()
                    assert not response.isError and value.get("success"),value
                    return value
                blocks=[]
                for i,(x,y) in enumerate([(60,140),(220,140),(140,210)],1):
                    blocks.append(await call("insert_electrical_symbol",{"symbol_name":str(LIB/"HT0001.dwg"),"x":x,"y":y,"attributes":{"TAGSTRIP":"XB","TERM01":str(i)}}))
                f,t=blocks[0]["handle"],blocks[1]["handle"]
                args={"from_handle":f,"from_connection":"X1TERM01","to_handle":t,"to_connection":"X4TERM01"}
                wire=await call("connect_electrical_terminals",args);target=wire["wire_handles"][0]
                await call("set_electrical_wire_number",{"wire_handle":target,"number":"501"})
                count=d.ModelSpace.Count
                again=await call("connect_electrical_terminals",args)
                assert again["status"]=="already_connected" and d.ModelSpace.Count==count
                branch_args={"terminal_handle":blocks[2]["handle"],"connection_name":"X8TERM01","wire_handle":target,"x":140,"y":140}
                branch=await call("branch_electrical_terminal_to_wire",branch_args)
                wanted={(f,"X1TERM01"),(t,"X4TERM01"),(blocks[2]["handle"],"X8TERM01")}
                assert branch["wire_number"]=="501" and {tuple(n) for n in branch["connections"]}==wanted
                count=d.ModelSpace.Count
                again=await call("branch_electrical_terminal_to_wire",branch_args)
                assert again["status"]=="already_connected" and d.ModelSpace.Count==count
                # Reversing endpoint order is also an existing connection.
                reverse={"from_handle":t,"from_connection":"X4TERM01","to_handle":f,"to_connection":"X1TERM01"}
                again=await call("connect_electrical_terminals",reverse)
                assert again["status"]=="already_connected" and d.ModelSpace.Count==count
                report["duplicate_entity_count"]=count
                async def check():
                    segments=[]
                    handles=[o.Handle for o in d.ModelSpace if o.ObjectName=="AcDbLine" and o.Layer=="MCP_WIRE"]
                    assert len(handles)==2,handles
                    for h in handles:
                        wire=await call("get_electrical_wire",{"wire_handle":h})
                        assert wire["wire_number"]=="501" and {tuple(n) for n in wire["connections"]}==wanted,wire
                        segments.append(wire)
                    return segments
                report["before"]=await check();d.Save();d.Close(False)
                d=method(lambda:app.Documents.Open)(str(path));ready(d)
                report["after"]=await check()
                count=d.ModelSpace.Count
                again=await call("connect_electrical_terminals",args)
                assert again["status"]=="already_connected" and d.ModelSpace.Count==count
                report["save_reopen"]="PASS"
    try:asyncio.run(run());report["status"]="PASS"
    except BaseException as exc:report["status"]="FAIL";report["error"]=repr(exc);raise
    finally:record();print(folder,flush=True)

if __name__=="__main__":main()
