"""Independent semantic acceptance of the synthetic multibranch project's evidence."""
import json,sys
from pathlib import Path
from collections import Counter
SPEC=json.loads((Path(__file__).resolve().parents[1]/"examples/branch-project/design.json").read_text(encoding="utf8"))

def validate(report,spec=SPEC):
    reports=report["reports"];tag=spec["tag"];number=spec["wire_number"];pins=set(spec["terminals"])
    assert all(r["success"] for r in reports.values()),"Report export failed"
    bom=reports["bom"]["rows"]
    assert len(bom)==1 and int(bom[0][1])==spec["quantity"] and bom[0][3:5]==[spec["catalog"],spec["manufacturer"]],"BOM mismatch"
    numbers=reports["terminal_numbers"]["rows"]
    assert len(numbers)==len(pins) and {r[1] for r in numbers}==pins,"Terminal inventory mismatch"
    handles={}
    for r in numbers:
        assert r[0]==tag and r[2]==number and r[6]==spec["sheet"],"Terminal number or sheet mismatch"
        assert r[8:11]==["HT0001",spec["manufacturer"],spec["catalog"]],"Terminal symbol/catalog mismatch"
        assert r[27].startswith("h=") and len(r[27])>2,"Missing terminal handle"
        handles[r[1]]=r[27][2:].upper()
    assert len(set(handles.values()))==len(pins),"Duplicate terminal handles"
    edges=[]
    for r in reports["from_to"]["rows"]:
        assert r[0]==number and r[2]==r[5]==tag and r[11]==r[12]==spec["sheet"],"From/To number/tag/sheet mismatch"
        assert r[3] in pins and r[6] in pins and r[3]!=r[6],"Invalid From/To endpoint"
        edges.append(frozenset([r[3],r[6]]))
    assert len(edges)==len(pins)-1 and len(set(edges))==len(edges),"Expected distinct spanning connections"
    reached={next(iter(pins))}
    while True:
        grown=reached | set().union(*(e for e in edges if e & reached))
        if grown==reached:break
        reached=grown
    assert reached==pins,"Disconnected From/To graph"
    incidence=[]
    for r in reports["terminal_plan"]["rows"]:
        assert r[10]==tag and r[12] in pins and r[26]==spec["sheet"],"Terminal plan identity mismatch"
        assert r[28].upper()=="H="+handles[r[12]],"Terminal plan handle mismatch"
        present=0
        for remote,pin,num in [(r[2],r[3],r[8]),(r[23],r[22],r[17])]:
            if not any([remote,pin,num]):continue
            assert remote==tag and pin in pins and pin!=r[12] and num==number,"Dangling/wrong plan connection"
            incidence.append((r[12],pin));present+=1
        assert present,"Empty terminal plan row"
    wanted=Counter((a,b) for edge in edges for a in edge for b in edge if a!=b)
    assert Counter(incidence)==wanted,"Plan and From/To disagree"
    expected_nodes={(handles[p],spec["terminals"][p]) for p in pins}
    geometry=[]
    for wire in report["after"]:
        assert wire["success"] and wire["wire_number"]==number,"Reopened number mismatch"
        assert {(h.upper(),p) for h,p in wire["connections"]}==expected_nodes,"Reopened native network mismatch"
        geometry.append(frozenset([tuple(wire["start"]),tuple(wire["end"])]))
    assert Counter(geometry)==Counter(frozenset(map(tuple,line)) for line in spec["geometry"]),"Geometry differs from design"
    assert report["save_reopen"]=="PASS"
    return {"status":"PASS","bom_quantity":spec["quantity"],"terminals":len(pins),"from_to_connections":len(edges),"terminal_plan_connections":len(incidence),"wire_number":number,"scope":spec["scope"]}

def main():
    folder=Path(sys.argv[1]).resolve();report=json.loads((folder/"report.json").read_text(encoding="utf8"));result=validate(report)
    (folder/"semantic-acceptance.json").write_text(json.dumps(result,indent=2),encoding="utf8");print(json.dumps(result))

if __name__=="__main__":main()
