"""Independent acceptance: reopen saved demo drawings and regenerate native reports.

Does not create or repair CAD entities. Compares actual data to design.json,
not merely to success flags from the construction run.
"""
import argparse, asyncio, csv, json, sys, time
from datetime import datetime, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def validate_reports(reports, spec):
    bom=reports["bom"]["rows"]
    assert len(bom)==len(spec["bom"]), "Unexpected BOM rows"
    assert {r[3]:int(r[1]) for r in bom}==spec["bom"], "BOM quantities/catalog mismatch"
    assert all(r[4]=="KINTO_TEST" for r in bom), "Unexpected manufacturer"
    components=reports["components"]["rows"]
    assert len(components)==len(spec["component_tags"])
    assert sorted(r[1] for r in components)==sorted(spec["component_tags"])
    rows=reports["from_to"]["rows"]
    actual=sorted([[r[0],r[2],r[3],r[5],r[6],r[11],r[12]] for r in rows])
    assert actual==sorted(spec["connections"]), ("Native From/To mismatch",actual)
    return actual


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("folder");args=p.parse_args()
    folder=Path(args.folder).resolve();build=json.loads((folder/"build.json").read_text(encoding="utf8"))
    spec=json.loads((ROOT/"examples/relay-demo/design.json").read_text(encoding="utf8"))
    assert build["status"]=="BUILT_REQUIRES_INDEPENDENT_VERIFICATION"
    paths=[Path(x) for x in build["pages"]]
    assert [p.name for p in paths]==spec["pages"] and all(p.parent==folder for p in paths)
    out=folder/datetime.now().strftime("verification-%Y%m%d-%H%M%S");out.mkdir()
    result={"status":"RUNNING","calls":[],"reopened":[],"drawing_checks":[]}
    def record():
        (out/"verification.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    from src.autocad.connection import get_connection
    from src.autocad.utils import get_block_attributes
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    app=get_connection()._app
    def read_ready(read):
        # Retry only read-only COM discovery. Never repeat Open/Close or CAD writes.
        error=None
        for _ in range(30):
            try:
                return read()
            except (AttributeError, TypeError) as exc:
                error=exc
                time.sleep(.2)
        raise error

    async def verify():
        async with stdio_client(StdioServerParameters(command=sys.executable,args=["-m","src.server"],cwd=str(ROOT))) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=65)) as session:
                await session.initialize()
                async def call(name,args):
                    attempts=3 if name.startswith("get_") else 1
                    for attempt in range(attempts):
                        response=await session.call_tool(name,args)
                        data=response.structuredContent or json.loads(next(c.text for c in response.content if c.type=="text"))
                        result["calls"].append({"tool":name,"attempt":attempt+1,"result":data});record()
                        if not response.isError and data.get("success"):
                            return data
                        if attempt+1<attempts:
                            await asyncio.sleep(.5)
                    raise AssertionError(data)
                project=await call("get_electrical_project",{})
                assert Path(project["project"])==Path(build["project"])
                assert {Path(p) for p in project["drawings"]}==set(paths)
                for sheet,path in enumerate(paths,1):
                    existing=[d for d in app.Documents if Path(d.FullName)==path]
                    if existing:
                        doc=existing[0]
                        if not doc.Saved:
                            # Preserve view/metadata changes only after confirming all fixture attributes.
                            for key,item in build["entities"].items():
                                if Path(item["drawing"])==path:
                                    assert get_block_attributes(doc.HandleToObject(item["handle"]))==build["final_attributes"][key]
                            doc.Save()
                        doc.Close(False)
                    opener=read_ready(lambda: app.Documents.Open)
                    doc=opener(str(path))
                    read_ready(lambda: doc.FullName)
                    time.sleep(.3)
                    result["reopened"].append(str(path))
                    wd=next(o for o in doc.ModelSpace if o.ObjectName=="AcDbBlockReference" and o.Name=="WD_M")
                    assert get_block_attributes(wd)["SHEET"]==str(sheet)
                    for key,item in build["entities"].items():
                        if Path(item["drawing"])!=path:continue
                        obj=doc.HandleToObject(item["handle"])
                        attrs=get_block_attributes(obj)
                        assert obj.Name==item["block"] and list(obj.InsertionPoint)==item["position"]
                        expected_attrs=build["final_attributes"][key]
                        for read_attempt in range(3):
                            if attrs==expected_attrs:break
                            result.setdefault("attribute_read_retries",[]).append({"component":key,"attempt":read_attempt+1,"difference":{k:[expected_attrs.get(k),attrs.get(k)] for k in expected_attrs.keys()|attrs.keys() if expected_attrs.get(k)!=attrs.get(k)}})
                            await asyncio.sleep(.3)
                            attrs=get_block_attributes(doc.HandleToObject(item["handle"]))
                        assert attrs==expected_attrs,("Attribute persistence",key,attrs)
                        points=await call("get_electrical_connections",{"handle":item["handle"]})
                        assert points["connection_points"]==item["connection_points"]
                        if key in spec["signals"]:
                            code,number,prefix=spec["signals"][key]
                            assert attrs["SIGCODE"]==code and attrs["WIRENO"]==number and attrs["XREF"].startswith(prefix)
                        result["drawing_checks"].append({"component":key,"handle":item["handle"],"status":"PASS"})
                    for key,wire in build["wires"].items():
                        if Path(wire["drawing"])!=path:continue
                        expected_nodes=sorted(wire["connections"])
                        for handle in wire["wire_handles"]:
                            data=await call("get_electrical_wire",{"wire_handle":handle})
                            assert data["wire_number"]==spec["wire_numbers"][key]
                            assert sorted(data["connections"])==expected_nodes
                            # Every segment must remain orthogonal, including the routed return.
                            assert data["start"][0]==data["end"][0] or data["start"][1]==data["end"][1]
                reports={}
                for kind in ["bom","components","from_to"]:
                    reports[kind]=await call("export_electrical_project_report",{"project_path":build["project"],"report_type":kind,"output_path":str(out/(kind+".csv"))})
                result["verified_connections"]=validate_reports(reports,spec)
                result["bom"]=spec["bom"]
                with (out/"connections-readable.csv").open("w",encoding="utf-8-sig",newline="") as f:
                    writer=csv.writer(f);writer.writerow(["Wire","From tag","From terminal","To tag","To terminal","From sheet","To sheet"]);writer.writerows(result["verified_connections"])
    try:
        asyncio.run(verify());result["status"]="PASS"
    except BaseException as exc:
        result["status"]="FAIL";result["error"]=repr(exc);raise
    finally:
        record();print(out,flush=True)


if __name__=="__main__":main()
