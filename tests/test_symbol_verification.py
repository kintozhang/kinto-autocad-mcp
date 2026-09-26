from unittest.mock import MagicMock, patch
import pytest
from src.tools import native_electrical as native
from src.autocad.lisp_bridge import literal, parse_receipt


@pytest.mark.parametrize("returned", [None, "A1"])
def test_failed_insert_never_updates_existing_component(returned):
    conn, doc, obj = MagicMock(), MagicMock(), MagicMock()
    obj.Handle = "A1"
    doc.ModelSpace = [obj]
    with patch.object(native, "connection", return_value=(conn, doc)), patch.object(native, "evaluate", return_value=returned) as call:
        result = native.insert_symbol("HCR1", 10, 20, attributes={"TAG1": "NEW"})
    assert result["success"] is False
    assert call.call_count == 1
    doc.HandleToObject.assert_not_called()


@pytest.mark.parametrize("attributes", [{"TAG*": "K1"}, {"TAG1": "bad\nvalue"}, {"TAG1": 1}])
def test_invalid_attributes_rejected_before_insertion(attributes):
    with patch.object(native, "connection") as connect:
        assert not native.insert_symbol("HCR1", 10, 20, attributes=attributes)["success"]
    connect.assert_not_called()


def test_description_attributes_are_not_connection_points():
    obj = MagicMock()
    attrs = []
    for tag in ["X1TERM01", "X4TERM02", "X1TERMDESC01", "X1PIN01", "TERM01"]:
        a = MagicMock()
        a.TagString, a.TextString, a.InsertionPoint = tag, "", (1, 2, 0)
        attrs.append(a)
    obj.GetAttributes.return_value = attrs
    assert [p["connection"] for p in native._points(obj)] == ["X1TERM01", "X4TERM02"]


def test_partial_insert_reports_created_handle():
    conn, doc, obj = MagicMock(), MagicMock(), MagicMock()
    doc.ModelSpace = []
    doc.HandleToObject.return_value = obj
    obj.ObjectName = "AcDbBlockReference"
    with patch.object(native, "connection", return_value=(conn, doc)), patch.object(native, "evaluate", side_effect=["A2", None]):
        result = native.insert_symbol("HCR1", 10, 20, attributes={"TAG1":"K1"})
    assert not result["success"]
    assert result["created_handle"] == "A2"
    assert result["retry_safe"] is False


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "bad\ncommand", True])
def test_unsafe_lisp_arguments_rejected(value):
    with pytest.raises(ValueError):
        literal(value)


def test_receipt_parses_nested_native_results():
    assert parse_receipt('( "ok" (("A1" "X1TERM01") nil 1.25))') == ["ok", [["A1", "X1TERM01"], None, 1.25]]


@pytest.mark.parametrize("text", ['("ok"', '("ok" nil) extra', ')', '("ok" <Entity name: abc>)'])
def test_incomplete_or_unsupported_receipts_rejected(text):
    with pytest.raises(ValueError):
        parse_receipt(text)


@pytest.mark.parametrize("attributes,options", [
    ({"TAG1":"-112K1"},6), ({"tag1":"-112K1"},6),
    ({"TAGSTRIP":"X54"},6), ({"TAG2":"-112K1"},2), ({},2),
])
def test_explicit_parent_or_terminal_tag_suppresses_native_autotag(attributes,options):
    # Returning nil stops after insertion: inspect the native option before any edits.
    conn,doc=MagicMock(),MagicMock();doc.ModelSpace=[]
    with patch.object(native,"connection",return_value=(conn,doc)), patch.object(native,"evaluate",return_value=None) as execute:
        native.insert_symbol("HCR1",10,20,attributes=attributes)
    assert execute.call_count==1
    assert execute.call_args.args[1].endswith(" 1.0 "+str(options)+")")


def test_connector_plug_jack_suffixes_are_pins_but_descriptions_are_not():
    obj=MagicMock()
    values={'TERM01P':'4','TERM01J':'4','TERM02P':'6'}
    attrs=[]
    for tag in ['X4TERM01P','X1TERM01J','X4TERM02P','X4TERMDESC01P','X4WIRE01P','X4_TINY_DOT_DONT_REMOVE_01P','X4TERM01BAD',*values]:
        a=MagicMock();a.TagString=tag;a.TextString=values.get(tag,'');a.InsertionPoint=(1,2,0);attrs.append(a)
    obj.GetAttributes.return_value=attrs
    points=native._points(obj)
    assert [(p['connection'],p['terminal']) for p in points]==[('X4TERM01P','4'),('X1TERM01J','4'),('X4TERM02P','6')]
