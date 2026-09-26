import pytest
from unittest.mock import MagicMock,patch
from src.tools import native_branch as b

@pytest.mark.parametrize("point,expected",[([5,0,0],True),([0,0,0],True),([10,0,0],True),([5,1,0],False),([11,0,0],False),([5,0,1],False)])
def test_tap_is_on_selected_segment(point,expected):
    assert b.point_on_segment(point,[0,0,0],[10,0,0]) is expected

def test_invalid_tap_never_inserts():
    with patch.object(b,"connection",return_value=(MagicMock(),MagicMock())), \
         patch.object(b,"inspect_wire",return_value={"success":True,"start":[0,0,0],"end":[10,0,0]}), \
         patch.object(b,"evaluate") as evaluate:
        r=b.branch("A","X1TERM01","B",5,1)
    assert not r["success"] and r["created_wire_handles"]==[]
    evaluate.assert_not_called()


@pytest.mark.parametrize("attrs,api",[({"WIRENO":"501"},"c:wd_putwn"),({"WIRENOF":"501"},"c:wd_putwnf")])
def test_number_refresh_preserves_normal_or_fixed_kind(attrs,api):
    assert b.number_refresh_function(attrs,"501")==api

@pytest.mark.parametrize("attrs",[{}, {"WIRENO":"502"}, {"WIRENO":"501","WIRENOF":"501"}])
def test_ambiguous_number_kind_is_rejected(attrs):
    with pytest.raises(b.BridgeError):b.number_refresh_function(attrs,"501")

def test_electrically_connected_but_blank_pin_cache_is_rejected():
    doc=MagicMock();attr=MagicMock();attr.TagString="X8TERM01";attr.TextString=""
    doc.HandleToObject.return_value.GetAttributes.return_value=[attr]
    with pytest.raises(b.BridgeError,match="cache is stale"):
        b.verify_pin_numbers(doc,[("94B","X8TERM01")],"501")
