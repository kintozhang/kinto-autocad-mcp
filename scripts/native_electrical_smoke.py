"""Opt-in real stdio MCP Electrical test; writes only a new synthetic drawing."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--template", required=True)
    parser.add_argument("--library", required=True)
    args = parser.parse_args()
    if not args.write:
        parser.error("Use --write to create a new synthetic test drawing")
    template, library = Path(args.template), Path(args.library)
    for path in [template, library / "HCR1.dwg", library / "HT0001.dwg"]:
        if not path.is_file():
            parser.error("Missing installed resource: " + str(path))
    import pythoncom
    import win32com.client
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    folder = ROOT / "work" / "acceptance" / datetime.now().strftime("native-mcp-%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True)
    path = folder / "native-electrical.dwg"
    report = {"status":"started", "drawing":str(path), "template":str(template),
              "library":str(library), "scope":"Synthetic single DWG; no WDP/project reports", "calls":[]}
    def record():
        (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    pythoncom.CoInitialize()
    try:
        app = win32com.client.GetActiveObject("AutoCAD.Application")
        report["version"] = app.Version
        report["original_documents"] = [d.FullName for d in app.Documents]
        doc = app.Documents.Add(str(template))
        doc.SaveAs(str(path))
        # Only read-only readiness probes are retried after creation.
        for _ in range(30):
            try:
                if Path(app.ActiveDocument.FullName) == path and doc.ModelSpace.Count:
                    break
            except Exception:
                pass
            time.sleep(.2)
        baseline = {o.Handle for o in doc.ModelSpace}
        assert any(o.ObjectName == "AcDbBlockReference" and o.Name.upper() == "WD_M" for o in doc.ModelSpace)
        def guard():
            if Path(app.ActiveDocument.FullName) != path or int(app.ActiveDocument.GetVariable("CMDACTIVE")):
                raise RuntimeError("Target changed or CAD command active; inspect before retry")
        async def exercise():
            nonlocal doc
            params = StdioServerParameters(command=sys.executable, args=["-m", "src.server"], cwd=str(ROOT))
            async with stdio_client(params) as (r,w):
                async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=40)) as session:
                    await session.initialize()
                    async def call(name, arguments):
                        guard()
                        result = await session.call_tool(name, arguments)
                        data = result.structuredContent
                        if data is None:
                            data = json.loads(next(c.text for c in result.content if c.type == "text"))
                        report["calls"].append({"tool":name,"arguments":arguments,"result":data})
                        record()
                        if result.isError or data.get("success") is False:
                            raise RuntimeError(name + ": " + str(data))
                        return data
                    relay = await call("insert_electrical_symbol", {"symbol_name":str(library/"HCR1.dwg"),"x":120,"y":150,
                        "attributes":{"DESC1":"MCP SYNTHETIC RELAY", "TERM01":"A1", "TERM02":"A2"}})
                    terminal = await call("insert_electrical_symbol", {"symbol_name":str(library/"HT0001.dwg"),"x":70,"y":150,
                        "attributes":{"TAGSTRIP":"X1", "TERM01":"1"}})
                    assert relay["block"].upper() == "HCR1" and relay["attributes"]["TAG1"]
                    assert relay["position"] == [120,150,0] and terminal["position"] == [70,150,0]
                    for component in [relay, terminal]:
                        assert component["handle"] not in baseline
                        points = await call("get_electrical_connections", {"handle":component["handle"]})
                        assert points["connection_points"] == component["connection_points"]
                        assert not any("DESC" in p["connection"] for p in points["connection_points"])
                    wire = await call("connect_electrical_terminals", {"from_handle":terminal["handle"],"from_connection":"X1TERM01",
                        "to_handle":relay["handle"],"to_connection":"X4TERM01"})
                    assert wire["start"] == [71.25,150,0] and wire["end"] == [112.5,150,0]
                    wh = wire["wire_handles"][0]
                    numbered = await call("set_electrical_wire_number", {"wire_handle":wh,"number":"101"})
                    before = await call("get_electrical_wire", {"wire_handle":wh})
                    assert before["wire_number"] == "101"
                    expected = sorted([[terminal["handle"],"X1TERM01"],[relay["handle"],"X4TERM01"]])
                    assert sorted(before["connections"]) == expected
                    snapshots = {}
                    for component, connected_tag in [(relay,"X4TERM01"),(terminal,"X1TERM01")]:
                        obj = doc.HandleToObject(component["handle"])
                        attrs = {a.TagString:a.TextString for a in obj.GetAttributes()}
                        # Native numbering caches 101 in the connected X?TERM attribute.
                        expected_attrs = dict(component["attributes"])
                        expected_attrs[connected_tag] = "101"
                        assert attrs == expected_attrs, (attrs, expected_attrs)
                        snapshots[component["handle"]] = attrs
                    report["attributes_before_reopen"] = snapshots
                    guard()
                    doc.Save()
                    doc.Close(False)
                    doc = app.Documents.Open(str(path))
                    for _ in range(30):
                        try:
                            guard()
                            break
                        except Exception:
                            time.sleep(.2)
                    after = await call("get_electrical_wire", {"wire_handle":wh})
                    assert before == after
                    for component in [relay, terminal]:
                        obj = doc.HandleToObject(component["handle"])
                        actual = {a.TagString:a.TextString for a in obj.GetAttributes()}
                        assert actual == snapshots[component["handle"]]
                        points = await call("get_electrical_connections", {"handle":component["handle"]})
                        assert points["connection_points"] == component["connection_points"]
                    report["before_reopen"] = before
                    report["after_reopen"] = after
                    report["components"] = {"relay":relay,"terminal":terminal}
                    report["native_from_to"] = {"from":"X1:1", "to":relay["attributes"]["TAG1"]+":A1", "wire_number":"101", "native_connections":after["connections"]}
                    await call("zoom_extents", {})
                    doc.Save()
        asyncio.run(exercise())
        report["status"] = "PASS"
    except BaseException as exc:
        report["status"] = "FAIL"
        report["error"] = repr(exc)
        raise
    finally:
        record()
        print(str(folder / "report.json"), flush=True)
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
