from unittest.mock import MagicMock, patch
import pytest
from src.tools import native_cross_references as x

def rows():
    return [{"attributes":{"TAG1":"-K1","INST":"A","LOC":"B","XREFNO":"3.3-C"}},
            {"attributes":{"TAG2":"-K1","INST":"A","LOC":"B","CONTACT":"NO","XREF":"2.4-B"}}]

@pytest.mark.parametrize("fault",["missing_parent","duplicate_parent","wrong_location","empty_child","empty_parent","unsupported"])
def test_reference_matching_rejects_invalid_results(fault):
    r=rows()
    if fault=="missing_parent":r=r[1:]
    elif fault=="duplicate_parent":r.append(r[0])
    elif fault=="wrong_location":r[1]["attributes"]["LOC"]="C"
    elif fault=="empty_child":r[1]["attributes"]["XREF"]=""
    elif fault=="empty_parent":r[0]["attributes"]["XREFNO"]=""
    else:r[1]["attributes"]["CONTACT"]="OTHER"
    with pytest.raises(x.BridgeError):x.pairs(r,True)

def test_preflight_allows_blank_refs_but_postflight_does_not():
    r=rows();r[1]["attributes"]["XREF"]=""
    assert len(x.pairs(r,False))==1
    with pytest.raises(x.BridgeError):x.pairs(r,True)

def test_unsaved_member_is_rejected():
    conn=MagicMock();doc=MagicMock();doc.FullName="C:/test/page.dwg";doc.Saved=False
    conn.get_application.return_value.Documents=[doc]
    with pytest.raises(x.BridgeError,match="Save project"):
        x.snapshot(conn,{"drawings":[doc.FullName]},True)
    doc.ModelSpace.__iter__.assert_not_called()


def test_same_filename_in_other_directory_is_rejected():
    conn=MagicMock();first=MagicMock();second=MagicMock()
    first.FullName="C:/first/page.dwg";second.FullName="C:/second/page.dwg"
    conn.get_application.return_value.Documents=[first,second]
    with pytest.raises(x.BridgeError,match="Duplicate open"):
        x.snapshot(conn,{"drawings":[first.FullName]},True)


def test_nc_does_not_accept_only_no_parent_reference():
    r=rows()
    r.append({"attributes":{"TAG2":"-K1","INST":"A","LOC":"B","CONTACT":"NC","XREF":"2.4-B"}})
    with pytest.raises(x.BridgeError,match="reference was empty"):
        x.pairs(r,True)
    r[0]["attributes"]["XREFNC"]="3.3-D"
    result=x.pairs(r,True)
    assert [p["parent_reference_field"] for p in result]==["XREFNO","XREFNC"]
