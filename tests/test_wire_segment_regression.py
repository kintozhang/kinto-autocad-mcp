from unittest.mock import MagicMock, patch
from src.tools import native_electrical as electrical


def test_extra_terminal_self_loop_is_not_reported_as_success():
    conn, doc = MagicMock(), MagicMock()
    obj = doc.HandleToObject.return_value
    obj.ObjectName = "AcDbLine"
    obj.Layer = "MCP_WIRE"
    points = [[{"connection": "X1TERM02", "position": [147.5, 170, 0]}],
              [{"connection": "X4TERM01", "position": [208.75, 170, 0]}]]
    valid = [["8B3", "X1TERM02"], ["965", "X4TERM01"]]
    bad = [["965", "X1TERM01"], ["965", "X4TERM01"]]
    with patch.object(electrical, "connection", return_value=(conn, doc)), \
         patch.object(electrical, "_points", side_effect=points), \
         patch.object(electrical, "evaluate", side_effect=[["MCP_WIRE"], ["9BE", "9BF"]]), \
         patch.object(electrical, "network", side_effect=[valid, bad]):
        result = electrical.connect_terminals("8B3", "X1TERM02", "965", "X4TERM01")
    assert result["success"] is False
    assert result["created_wire_handles"] == ["9BE", "9BF"]
    assert result["retry_safe"] is False


def test_offset_terminal_route_uses_terminal_start_and_checks_every_segment():
    conn,doc=MagicMock(),MagicMock()
    obj=doc.HandleToObject.return_value;obj.ObjectName="AcDbLine";obj.Layer="MCP_WIRE"
    points=[[{"connection":"X1TERM02","position":[147.5,110,0]}],
            [{"connection":"X4TERM01","position":[208.75,90,0]}]]
    valid=[["9F3","X1TERM02"],["A64","X4TERM01"]]
    with patch.object(electrical,"connection",return_value=(conn,doc)), \
         patch.object(electrical,"_points",side_effect=points), \
         patch.object(electrical,"get_block_attributes",side_effect=[{"TAG2":"-K1"},{"TAGSTRIP":"X3"}]), \
         patch.object(electrical,"evaluate",side_effect=[["MCP_WIRE"],["ABA","ABB","ABC"]]) as evaluate, \
         patch.object(electrical,"network",side_effect=[valid,valid,valid]) as network:
        result=electrical.connect_terminals("9F3","X1TERM02","A64","X4TERM01")
    assert result["success"] and result["native_route_reversed"]
    expression=evaluate.call_args_list[-1].args[1]
    assert expression.index("208.75") < expression.index("147.5")
    assert network.call_count==3
    assert result["start"]==[147.5,110,0] and result["end"]==[208.75,90,0]


def test_existing_native_connection_never_submits_insert():
    conn,doc=MagicMock(),MagicMock()
    line=MagicMock();line.ObjectName="AcDbLine";line.Layer="MCP_WIRE";line.Handle="A1"
    line.StartPoint=[0,0,0];line.EndPoint=[10,0,0];doc.ModelSpace=[line]
    points=[[{"connection":"X1TERM01","position":[0,0,0]}],[{"connection":"X4TERM01","position":[10,0,0]}]]
    with patch.object(electrical,"connection",return_value=(conn,doc)), \
         patch.object(electrical,"_points",side_effect=points), \
         patch.object(electrical,"evaluate",return_value=["MCP_WIRE"]) as evaluate, \
         patch.object(electrical,"network",return_value=[["A","X1TERM01"],["B","X4TERM01"]]):
        result=electrical.connect_terminals("A","X1TERM01","B","X4TERM01")
    assert result["success"] and result["status"]=="already_connected"
    assert result["created_wire_handles"]==[] and not result["changed"]
    assert evaluate.call_count==1
