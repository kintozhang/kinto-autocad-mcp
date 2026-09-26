import pytest
from src.autocad.trebi_rules import page_navigation,page_reference,zone_at,profile

def test_logical_navigation_keeps_gaps():
    assert page_navigation(["14","50","100"],"50")=={"PAGE":"50","PREV":"14","NEXT":"100"}

@pytest.mark.parametrize("text",["112.10","2.4-B","I545","X15:5"])
def test_non_reference_labels_rejected(text):
    with pytest.raises(ValueError):page_reference(text,context="wire_reference")

def test_position_keeps_context():
    assert page_reference("300.2",context="module_position")["context"]=="module_position"
    with pytest.raises(ValueError):page_reference("300.2",context="unknown")

def test_full_width_frame_and_ten_zones():
    cfg=profile()
    assert cfg["title_bounds"]==[10,10,410,40]
    assert [zone_at(30+i*40) for i in range(10)]==list(range(10))
    assert zone_at(410)==9
    with pytest.raises(ValueError):zone_at(411)

def test_mechanical_profile_retained():
    from src.autocad.bilingual_titleblock import profile as mechanical
    assert mechanical()["block_name"]=="KINTO_TB_A3_ZH_EN"
    assert mechanical()["width"]==188 and mechanical()["height"]==55
