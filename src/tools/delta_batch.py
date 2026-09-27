"""Bounded Delta test recipe. Never a production localization approval."""
from pathlib import Path
import hashlib
from src.autocad.trebi_project_pages import plan as page_plan

ASSET_SHA256 = "14d6be8d1a4d68c402ce2800bac3978d01c81f218fce9bcac1b0d77c8da02e15"

def plan(spec):
    if not isinstance(spec, dict) or set(spec) != {"schema_version", "recipe", "purpose", "manifest", "symbol_path"}:
        raise ValueError("Delta recipe requires exact schema, recipe, purpose, manifest and symbol_path")
    if type(spec["schema_version"]) is not int or spec["schema_version"] != 2 or spec["recipe"] != "delta_r2_output_poc" or spec["purpose"] != "test_only":
        raise ValueError("Only Delta test_only recipe v2 is supported; production localization is blocked")
    pages=page_plan(spec["manifest"])
    entries=spec["manifest"]["entries"]
    if len(entries)!=1 or pages["effective_drawing_count"]!=1:
        raise ValueError("Delta POC requires exactly one effective drawing")
    entry=entries[0]; name=entry.get("drawing_file")
    if not isinstance(name,str) or Path(name).name!=name or Path(name).suffix.lower()!=".dwg":
        raise ValueError("Local DWG filename required")
    if not isinstance(spec["symbol_path"],str): raise ValueError("Absolute verified symbol path required")
    asset=Path(spec["symbol_path"])
    if not asset.is_absolute() or asset.name!="HBB1_KINTO_R2_EC0902_TEST.dwg" or not asset.is_file():
        raise ValueError("Verified R2 v2 symbol file required")
    try:
        asset_hash=hashlib.sha256(asset.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError("Cannot read verified R2 asset: "+str(exc)) from exc
    if asset_hash!=ASSET_SHA256:
        raise ValueError("R2 symbol differs from the independently verified v2 asset")
    sheet=entry["logical_page"]
    components=[dict(id="r2",role="delta_r2_test",symbol=asset.stem,symbol_path=str(asset),drawing_page=sheet,x=100,y=250,
        attributes={"TAG1":f"-{sheet}A1","MFG":"DELTA","CAT":"R2-EC0902D0","DESC2":"TEST ONLY - ADDRESS UNASSIGNED"}),
        dict(id="lamp",role="delta_lamp_test",symbol="HLT1G",drawing_page=sheet,x=280,y=238,
        attributes={"TAG1":f"-{sheet}H1","MFG":"KINTO_TEST","CAT":"LAMP_24V_TEST","DESC1":"O518 FUNCTION TEST","TERM01":"1","TERM02":"2"})]
    for n,x,y in [(1,50,128),(2,240,238),(3,330,238),(4,115,70),(5,140,70),(6,165,70),(7,185,70)]:
        components.append(dict(id=f"t{n}",role="terminal",symbol="HT0001",drawing_page=sheet,x=x,y=y,attributes={"TAGSTRIP":"-XPOC","TERM01":str(n)}))
    connections=[]
    def wire(id,a,ap,b,bp,number,layer):
        connections.append(dict(id=id,from_id=a,from_connection=ap,to_id=b,to_connection=bp,wire_number=number,wire_layer=layer))
    wire("io_supply","t1","X1TERM01","r2","X4TERM65","TEST24","TEST_24V")
    wire("output","r2","X1TERM33","t2","X4TERM01","TEST518","TEST_SIGNAL")
    wire("lamp_feed","t2","X1TERM01","lamp","X4TERM01","TEST518","TEST_SIGNAL")
    wire("lamp_return","lamp","X1TERM02","t3","X4TERM01","TEST0","TEST_0V")
    for n,pin,number,layer in [(4,73,"PWR24","TEST_MODULE_24V"),(5,74,"PWR0","TEST_MODULE_0V"),(6,75,"FG_TEST","TEST_FG"),(7,76,"TEST0","TEST_0V")]:
        wire(f"module_{n}","r2",f"X8TERM{pin}",f"t{n}","X2TERM01",number,layer)
    return dict(success=True,submitted=False,pages=pages,component_plan={"components":[{"id":"r2","tag":f"-{sheet}A1"},{"id":"lamp","tag":f"-{sheet}H1"}]},
        components=components,connections=connections,expected_references=[],scope="delta_r2_output_poc_test_only",production_ready=False,
        limitations=["External power boundary terminals only", "Hardware revision, NC50 address and original terminals unconfirmed", "Test lamp and pins, no production selection", "Electrical smart remote I/O test symbol; EtherCAT topology and NC50 program not verified"])

def verify_insert(result):
    points=result.get("connection_points",[])
    actual={p["connection"]:p["terminal"] for p in points}
    from src.tools.delta_module_inventory import expected_smart_symbol_connections
    expected=expected_smart_symbol_connections()
    if len(points)!=76 or actual!=expected: raise RuntimeError("Inserted R2 terminal inventory differs from verified asset")
    return {"success":True,"connection_points":76}
