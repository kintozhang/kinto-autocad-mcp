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
    folder=ROOT/"work/acceptance"/datetime.now().strftime("crossing-%Y%m%d-%H%M%S");folder.mkdir()
    path=folder/(folder.name+".dwg");report={"status":"RUNNING","drawing":str(path),"calls":[]}
    def record():(folder/"report.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    app=get_connection().get_application()
    d=method(lambda:app.Documents.Add)("C:/Users/James/AppData/Local/Autodesk/AutoCAD Electrical 2026/R25.1/chs/Template/ACE_Din_a3_Color.dwt")
    ready(d);d.SaveAs(str(path));ready(d)
    async def run():
        nonlocal d
        async with stdio_client(StdioServerParameters(command=sys.executable,args=["-m","src.server"],cwd=str(ROOT),env={**os.environ,"KINTO_MCP_EXPERIMENTAL":"0"})) as (r,w):
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
                for i,(x,y) in enumerate([(60,140),(220,140),(140,210),(140,70)],1):
                    blocks.append(await call("insert_electrical_symbol",{"symbol_name":str(LIB/"HT0001.dwg"),"x":x,"y":y,"attributes":{"TAGSTRIP":"XT","TERM01":str(i)}}))
                wanted={}
                for i,ip,j,jp,number in [(0,"X1TERM01",1,"X4TERM01","401"),(2,"X8TERM01",3,"X2TERM01","402")]:
                    f,t=blocks[i]["handle"],blocks[j]["handle"]
                    wire=await call("connect_electrical_terminals",{"from_handle":f,"from_connection":ip,"to_handle":t,"to_connection":jp})
                    wanted[number]={(f,ip),(t,jp)}
                    await call("set_electrical_wire_number",{"wire_handle":wire["wire_handles"][0],"number":number})
                async def check():
                    seen=set();segments=[]
                    handles=[o.Handle for o in d.ModelSpace if o.ObjectName=="AcDbLine" and o.Layer=="MCP_WIRE"]
                    for h in handles:
                        wire=await call("get_electrical_wire",{"wire_handle":h})
                        number=wire["wire_number"];assert number in wanted,wire
                        assert {tuple(v) for v in wire["connections"]}==wanted[number],wire
                        seen.add(number);segments.append(wire)
                    assert seen=={"401","402"},seen
                    return segments
                report["before"]=await check();d.Save();d.Close(False)
                d=method(lambda:app.Documents.Open)(str(path));ready(d)
                report["after"]=await check();report["save_reopen"]="PASS"
    try:asyncio.run(run());report["status"]="PASS"
    except BaseException as exc:report["status"]="FAIL";report["error"]=repr(exc);raise
    finally:record();print(folder,flush=True)

if __name__=="__main__":main()
