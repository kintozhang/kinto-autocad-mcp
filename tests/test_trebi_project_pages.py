import copy
import pytest
from src.autocad.trebi_project_pages import plan,resolve_reference

def drawing(page,included=True):
    return {"id":"sheet-"+page,"kind":"drawing","logical_page":page,"include_in_total":included}

def test_326_of_96_is_not_a_physical_page_index():
    manifest={"schema_version":1,"entries":[drawing(str(i)) for i in range(95)]+[{"id":"manual","kind":"attachment","include_in_total":False},drawing("326")]}
    result=plan(manifest)
    assert result["effective_drawing_count"]==96
    assert result["drawings"][-1]["title_fields"]=={"PAGE":"326","OF":"96","PREV":"94","NEXT":"-"}
    assert resolve_reference(manifest,"326.7",context="wire_reference")=={"logical_page":"326","zone":7,"context":"wire_reference","entry_id":"sheet-326"}

def test_explicit_order_gaps_exclusions_and_attachments():
    m={"schema_version":1,"entries":[drawing("326"),drawing("325",False),drawing("54"),{"id":"manual","kind":"attachment","include_in_total":False}]}
    r=plan(m)
    assert r["logical_pages"]==["326","54"]
    assert r["drawings"][0]["title_fields"]["NEXT"]=="54"
    assert r["drawings"][1]["title_fields"] is None
    assert r["drawings"][2]["title_fields"]["OF"]=="2"
    with pytest.raises(ValueError):resolve_reference(m,"325.7",context="wire_reference")
    with pytest.raises(ValueError):resolve_reference(m,"112.7",context="wire_reference")

@pytest.mark.parametrize("page,group",[("0","overview_power"),("14","overview_power"),("50","distribution_drives"),("63","distribution_drives"),("100","field_functions"),("123","field_functions"),("300","main_cabinet_io"),("329","main_cabinet_io"),("400","other_cabinets"),("421","other_cabinets"),("500","operator_station"),("330",None)])
def test_group_boundaries(page,group):
    assert plan({"schema_version":1,"entries":[drawing(page)]})["drawings"][0]["group"]==group

@pytest.mark.parametrize("entries",[[drawing("54"),drawing("54")],[drawing("054")],[drawing("54",False)],[{"id":"manual","kind":"attachment","include_in_total":True}],[{"id":"x","kind":"drawing","logical_page":"54"}],[drawing("54",1)]])
def test_ambiguous_count_rejected(entries):
    with pytest.raises(ValueError):plan({"schema_version":1,"entries":entries})

def test_overlapping_groups_rejected():
    with pytest.raises(ValueError,match="Overlapping"):
        plan({"schema_version":1,"entries":[drawing("54")]},[{"id":"a","first":0,"last":54},{"id":"b","first":54,"last":100}])

def test_insert_changes_count_and_navigation_without_renumbering():
    m={"schema_version":1,"entries":[drawing("325"),drawing("327")]}
    before=copy.deepcopy(m)
    m["entries"].insert(1,drawing("326"))
    assert plan(before)["logical_pages"]==["325","327"]
    assert plan(m)["logical_pages"]==["325","326","327"]
    assert plan(m)["drawings"][0]["title_fields"]=={"PAGE":"325","OF":"3","PREV":"-","NEXT":"326"}
