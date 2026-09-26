"""Opt-in MCP mechanical dimensions acceptance on a new synthetic DWG."""
import argparse,asyncio,json,math,os,sys,time
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument("--write",action="store_true",required=True);args=p.parse_args()
    import win32com.client
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    folder=ROOT/"work/acceptance"/datetime.now().strftime("dimensions-%Y%m%d-%H%M%S");folder.mkdir()
    path=folder/"plate-dimensioned.dwg"
    report={"status":"RUNNING","drawing":str(path),"calls":[],"dimensions":[]}
    def record():(folder/"report.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    app=win32com.client.GetActiveObject("AutoCAD.Application")
    # Retry only method discovery while AutoCAD is temporarily busy.
    for attempt in range(20):
        try:
            add_document=app.Documents.Add
            break
        except AttributeError:
            if attempt==19:raise
            time.sleep(.25)
    doc=add_document();doc.SetVariable("INSUNITS",4);doc.SaveAs(str(path));time.sleep(.3)
    assert doc.ModelSpace.Count==0
    async def run():
        nonlocal doc
        params=StdioServerParameters(command=sys.executable,args=["-m","src.server"],cwd=str(ROOT),env={**os.environ,"KINTO_MCP_EXPERIMENTAL":"1"})
        async with stdio_client(params) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=45)) as session:
                await session.initialize()
                async def call(name,args):
                    assert Path(app.ActiveDocument.FullName)==path
                    response=await session.call_tool(name,args)
                    data=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                    report["calls"].append({"tool":name,"arguments":args,"result":data});record()
                    assert not response.isError and data.get("success"),data
                    return data
                rect=await call("draw_rectangle",{"x1":0,"y1":0,"x2":120,"y2":80,"layer":"MCP_OUTLINE"})
                holes=[];lines=[]
                for x,y in [(10,10),(110,10),(110,70),(10,70)]:
                    result=await call("draw_circle",{"cx":x,"cy":y,"radius":3,"layer":"MCP_HOLES"});holes.append((result["handle"],x,y))
                    for x1,y1,x2,y2 in [(x-4,y,x+4,y),(x,y-4,x,y+4)]:
                        line=await call("draw_line",{"x1":x1,"y1":y1,"x2":x2,"y2":y2,"layer":"MCP_CENTRES"});lines.append((line["handle"],[x1,y1,0],[x2,y2,0]))
                await call("draw_text",{"x":0,"y":96,"text":"MCP DIMENSION TEST / mm / FIXED GEOMETRY","height":3})
                for endpoints,expected in [([0,0,120,0,60,-18],120),([0,0,0,80,-18,40],80),([10,10,110,10,60,-8],100),([110,10,110,70,133,40],60)]:
                    args=dict(zip(["x1","y1","x2","y2","text_x","text_y"],endpoints));args["drawing_path"]=str(path)
                    dim=await call("add_aligned_dimension",args)
                    assert math.isclose(dim["measurement"],expected,abs_tol=1e-6) and dim["text_override"]==""
                    report["dimensions"].append([dim["handle"],expected,"AcDbAlignedDimension"])
                dim=await call("add_diameter_dimension",{"drawing_path":str(path),"circle_handle":holes[2][0],"leader_length":12})
                report["dimensions"].append([dim["handle"],6,"AcDbDiametricDimension"])
                library=await call("get_symbol_list",{"category":"coils"})
                assert library["symbols"] and all(Path(item["path"]).is_file() for item in library["items"])
                assert all(n.upper()=="HCR1" for n in library["symbols"])
                def geometry():
                    assert math.isclose(doc.HandleToObject(rect["handle"]).Area,9600)
                    assert doc.HandleToObject(rect["handle"]).Closed
                    for handle,x,y in holes:
                        obj=doc.HandleToObject(handle);assert list(obj.Center)==[x,y,0] and obj.Radius==3
                    for handle,start,end in lines:
                        obj=doc.HandleToObject(handle);assert list(obj.StartPoint)==start and list(obj.EndPoint)==end
                    assert doc.ModelSpace.Count==19,doc.ModelSpace.Count
                geometry();await call("zoom_extents",{});doc.Save();doc.Close(False);time.sleep(.5)
                doc=app.Documents.Open(str(path));time.sleep(.3);geometry()
                for handle,expected,kind in report["dimensions"]:
                    dim=await call("get_dimension_info",{"drawing_path":str(path),"handle":handle})
                    assert dim["object_type"]==kind and math.isclose(dim["measurement"],expected,abs_tol=1e-6)
                    assert dim["text_override"]=="" and dim["associative"] is False
                report["save_reopen"]="PASS";report["entity_count"]=19
    try:
        asyncio.run(run());report["status"]="PASS"
    except BaseException as exc:
        report["status"]="FAIL";report["error"]=repr(exc);raise
    finally:
        record();print(folder,flush=True)

if __name__=="__main__":main()
