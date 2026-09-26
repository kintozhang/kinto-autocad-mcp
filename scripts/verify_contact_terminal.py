"""Read-only report validation and saved-DWG reopen for the synthetic 3-page fixture."""
import json,sys,time
from pathlib import Path
from src.autocad.connection import get_connection
from src.autocad.utils import get_block_attributes

def validate(r):
    assert all(v["success"] for v in r.values())
    assert len(r["bom"]["rows"]) == 4
    assert {x[3]:int(x[1]) for x in r["bom"]["rows"]} == {"RELAY_DEMO":1,"FUSE_DEMO":1,"PUSHBUTTON_DEMO":1,"TERMINAL_DEMO":4}
    expected = {("100","-X1","1","-F1","1"),("101","-F1","2","-S1","13"),("102","-X1","2","-K1","A2"),("103","-S1","14","-K1","A1"),("201","-X2","1","-K1","13"),("202","-K1","14","-X2","2")}
    assert len(r["from_to"]["rows"]) == 6
    assert {(x[0],x[2],x[3],x[5],x[6]) for x in r["from_to"]["rows"]} == expected
    assert len(r["terminal_numbers"]["rows"]) == 4
    assert {(x[0],x[1],x[2]) for x in r["terminal_numbers"]["rows"]} == {("-X1","1","100"),("-X1","2","102"),("-X2","1","201"),("-X2","2","202")}
    assert len(r["terminal_plan"]["rows"]) == 4
    assert {(x[10],x[12],x[8] or x[17],x[2] or x[23],x[3] or x[22]) for x in r["terminal_plan"]["rows"]} == {("-X1","1","100","-F1","1"),("-X1","2","102","-K1","A2"),("-X2","1","201","-K1","13"),("-X2","2","202","-K1","14")}

def main():
    p=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve()
    assert out.is_relative_to(p)
    r=json.loads((out/"results.json").read_text(encoding="utf8"));validate(r)
    app=get_connection().get_application();refs={}
    for name,handle,field,want in [("02-CONTROL.dwg","931","XREFNO","3.3-C"),("03-CONTACT.dwg","8B3","XREF","2.4-B")]:
        path=p/name
        docs=[d for d in app.Documents if Path(d.FullName)==path]
        if docs:
            d=docs[0];d.Activate();assert d.Saved,"Unsaved drawing; inspect before closing";d.Close(False)
        # Retry only read-only COM method discovery, never repeat an Open write.
        for attempt in range(10):
            try:
                opener=app.Documents.Open;break
            except AttributeError:
                if attempt==9:raise
                time.sleep(.3)
        d=opener(str(path));time.sleep(.3)
        attrs=get_block_attributes(d.HandleToObject(handle));assert attrs[field]==want,attrs
        refs[name]={"handle":handle,"attributes":attrs,"save_reopen":"PASS"}
    result={"status":"PASS","references":refs,"reports":"PASS","scope":"Synthetic 3-page fixture. Extra native wire manually repaired. Cross-reference API probe is not a released MCP tool."}
    (out/"acceptance.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    print(out/"acceptance.json")

if __name__ == "__main__": main()
