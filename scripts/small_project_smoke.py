"""Build a fresh two-sheet synthetic relay project through real stdio MCP.

Native project bootstrap uses the documented WDP API. Construction and reports
use MCP. Run verify_small_project.py separately for independent acceptance.
"""
import argparse
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--library", required=True)
    args = parser.parse_args()
    from src.autocad.connection import get_connection
    from src.autocad.lisp_bridge import evaluate, literal
    from src.autocad.utils import get_block_attributes
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    template, library = Path(args.template), Path(args.library)
    assert template.is_file()
    folder = ROOT / "work" / "projects" / datetime.now().strftime("relay-demo-%Y%m%d-%H%M%S")
    folder.mkdir(parents=True, exist_ok=False)
    wdp = folder / "RELAY-DEMO.wdp"
    pages = [folder/"01-SUPPLY.dwg", folder/"02-CONTROL.dwg"]
    report = {"status":"BUILDING", "project":str(wdp), "pages":[str(p) for p in pages],
              "scope":"Synthetic 24V relay demonstration, no procurement ratings or safety certification", "calls":[], "entities":{}, "wires":{}}
    def record():
        (folder/"build.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    c = get_connection()
    app = c._app
    report["previous_project"] = evaluate(c,"(ace_getactiveproject)")
    record()
    expr = '((lambda (/ p) (setq p (c:wd_proj_wdp_data)) (c:wd_proj_wdp_write ' + literal(wdp.as_posix()) + ' (nth 2 p) (nth 3 p) (nth 4 p) nil) T))'
    evaluate(c,expr)
    try:
        evaluate(c,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)')
    except Exception as exc:
        # Activation may briefly invalidate COM. Never retry the write.
        report["activation_observation"] = str(exc)
    time.sleep(.5)
    c = get_connection()
    app = c._app
    assert Path(evaluate(c,"(ace_getactiveproject)")) == wdp
    docs=[]
    for i,path in enumerate(pages,1):
        doc=app.Documents.Add(str(template));doc.SaveAs(str(path));time.sleep(.3)
        assert evaluate(c,'(c:ace_add_dwg_to_project '+literal(path.as_posix())+' (list "" "" '+literal("SYNTHETIC RELAY DEMO / "+str(i))+ ' nil nil))')==1
        wd=next(o for o in doc.ModelSpace if o.ObjectName=="AcDbBlockReference" and o.Name=="WD_M")
        for key,value in {"SHEET":str(i),"XREFFMT":"%S.%N","ALT_XREFFMT":"%S.%N"}.items():
            assert evaluate(c,'(c:wd_modattrval (handent '+literal(wd.Handle)+') '+literal(key)+' '+literal(value)+' nil)')==1
        evaluate(c,'(progn (c:wd_read_dwg_params) T)')
        doc.Save();docs.append(doc)
    target=pages[0]
    async def build():
        nonlocal target
        params=StdioServerParameters(command=sys.executable,args=["-m","src.server"],cwd=str(ROOT))
        async with stdio_client(params) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=65)) as session:
                await session.initialize()
                async def call(name, arguments):
                    assert Path(app.ActiveDocument.FullName)==target
                    result=await session.call_tool(name,arguments)
                    data=result.structuredContent or json.loads(next(c.text for c in result.content if c.type=="text"))
                    report["calls"].append({"drawing":str(target),"tool":name,"arguments":arguments,"result":data});record()
                    if result.isError or not data.get("success", True):
                        raise RuntimeError(name+": "+str(data))
                    return data
                async def component(key,sym,x,y,attrs):
                    result=await call("insert_electrical_symbol",{"symbol_name":str(library/(sym+".dwg")),"x":x,"y":y,"attributes":attrs})
                    report["entities"][key]={"drawing":str(target),**result};record()
                    return result
                async def connect(key,frm,ft,to,tt,number=None):
                    result=await call("connect_electrical_terminals",{"from_handle":report["entities"][frm]["handle"],"from_connection":ft,"to_handle":report["entities"][to]["handle"],"to_connection":tt})
                    report["wires"][key]={"drawing":str(target),**result};record()
                    if number:
                        await call("set_electrical_wire_number",{"wire_handle":result["wire_handles"][0],"number":number})
                docs[0].Activate();target=pages[0]
                await call("get_electrical_project",{})
                await component("X1_1","HT0001",70,200,{"TAGSTRIP":"X1","TERM01":"1","DESC1":"+24V INPUT","MFG":"KINTO_TEST","CAT":"TERMINAL_DEMO"})
                await component("F1","HFU1",120,200,{"TAG1":"-F1","TERM01":"1","TERM02":"2","DESC1":"FUSE DEMO - RATING TBD","MFG":"KINTO_TEST","CAT":"FUSE_DEMO"})
                await component("SOURCE24","HA1S1",200,200,{"SIGCODE":"DEMO_24V","DESC1":"+24V TO SHEET 2"})
                await component("X1_2","HT0001",70,100,{"TAGSTRIP":"X1","TERM01":"2","DESC1":"0V RETURN","MFG":"KINTO_TEST","CAT":"TERMINAL_DEMO"})
                await component("SOURCE0","HA1S1",200,100,{"SIGCODE":"DEMO_0V","DESC1":"0V TO SHEET 2"})
                await connect("input","X1_1","X1TERM01","F1","X4TERM01","100")
                await connect("source24","F1","X1TERM02","SOURCE24","X4TERM01","101")
                await connect("source0","X1_2","X1TERM01","SOURCE0","X4TERM01","102")
                await call("draw_text",{"x":60,"y":245,"text":"01 SUPPLY / SYNTHETIC 24V RELAY DEMO","height":4})
                await call("draw_text",{"x":60,"y":75,"text":"TEST CATALOG DATA / NOT FOR CONSTRUCTION","height":3})
                docs[0].Save()
                docs[1].Activate();target=pages[1]
                await component("DEST24","HA1D3",60,200,{"SIGCODE":"DEMO_24V","DESC1":"+24V FROM SHEET 1"})
                await component("S1","HPB11",110,200,{"TAG1":"-S1","TERM01":"13","TERM02":"14","DESC1":"MOMENTARY ON","MFG":"KINTO_TEST","CAT":"PUSHBUTTON_DEMO"})
                await component("K1","HCR1",180,200,{"TAG1":"-K1","TERM01":"A1","TERM02":"A2","DESC1":"24V COIL DEMO","MFG":"KINTO_TEST","CAT":"RELAY_DEMO"})
                await component("DEST0","HA1D3",60,100,{"SIGCODE":"DEMO_0V","DESC1":"0V FROM SHEET 1"})
                await connect("dest24","DEST24","X1TERM01","S1","X4TERM01")
                await connect("switched","S1","X1TERM02","K1","X4TERM01","103")
                await connect("return","K1","X1TERM02","DEST0","X1TERM01")
                await call("draw_text",{"x":60,"y":245,"text":"02 CONTROL / PRESS S1 TO ENERGIZE K1","height":4})
                await call("draw_text",{"x":60,"y":75,"text":"FUNCTION DEMO ONLY / NO SAFETY CIRCUIT","height":3})
                docs[1].Save()
                for i,doc in enumerate(docs):
                    doc.Activate();target=pages[i]
                    await call("update_electrical_signals",{"project_path":str(wdp)})
                    doc.Save()
                for kind in ["bom","components","from_to"]:
                    await call("export_electrical_project_report",{"project_path":str(wdp),"report_type":kind,"output_path":str(folder/("native-"+kind+".csv"))})
                report["final_attributes"]={}
                for i,doc in enumerate(docs):
                    doc.Activate();target=pages[i]
                    for key,item in report["entities"].items():
                        if item["drawing"]==str(target):
                            report["final_attributes"][key]=get_block_attributes(doc.HandleToObject(item["handle"]))
                    await call("zoom_extents",{})
                    doc.Save()
    try:
        asyncio.run(build());report["status"]="BUILT_REQUIRES_INDEPENDENT_VERIFICATION"
    except BaseException as exc:
        report["error"]=repr(exc);report["status"]="FAILED";raise
    finally:
        record();print(str(folder),flush=True)


if __name__=="__main__":
    main()
