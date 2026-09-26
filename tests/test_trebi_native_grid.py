import pytest
from src.autocad.trebi_native_grid import settings
from src.autocad.trebi_rules import zone_at

def test_native_grid_matches_frame():
    cfg=settings("112")
    assert cfg["REFNUMS"]=="5" and cfg["SHEET"]=="112"
    assert cfg["XREFFMT"]==cfg["ALT_XREFFMT"]=="%S.%N"
    assert cfg["CHAR_H"]=="0,1,2,3,4,5,6,7,8,9"
    for i in range(10):
        x=float(cfg["DATUMX"])+(i+.5)*float(cfg["DISTH"])
        assert zone_at(x)==i

@pytest.mark.parametrize("sheet",[112,"01","112.8","","-1"])
def test_invalid_sheet_preflight(sheet):
    with pytest.raises(ValueError):settings(sheet)


def test_wrong_frame_never_submits(tmp_path):
    from unittest.mock import MagicMock,patch
    from src.autocad.trebi_native_grid import configure
    conn=MagicMock();doc=conn.get_active_document.return_value
    doc.FullName=str(tmp_path/"test.dwg");doc.ModelSpace=[]
    with patch("src.autocad.trebi_native_grid.evaluate") as execute:
        with pytest.raises(ValueError,match="TREBI frame"):
            configure(conn,doc.FullName,"112")
        execute.assert_not_called()


def test_wrong_drawing_never_submits(tmp_path):
    from unittest.mock import MagicMock,patch
    from src.autocad.trebi_native_grid import configure
    conn=MagicMock();conn.get_active_document.return_value.FullName=str(tmp_path/"other.dwg")
    with patch("src.autocad.trebi_native_grid.evaluate") as execute:
        with pytest.raises(ValueError,match="Wrong drawing"):
            configure(conn,tmp_path/"test.dwg","112")
        execute.assert_not_called()
