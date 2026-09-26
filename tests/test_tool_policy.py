import ast
from pathlib import Path
from unittest.mock import MagicMock,patch
import pytest
from src.tool_policy import catalogue,register
from src.tools import dimensions,symbol_library,wires,components


def test_every_tool_has_exactly_one_capability_entry():
    tree=ast.parse((Path(__file__).resolve().parents[1]/"src/server.py").read_text(encoding="utf8"))
    tools=[n.name for n in tree.body if isinstance(n,ast.FunctionDef) and any(isinstance(d,ast.Call) and isinstance(d.func,ast.Name) and d.func.id=="registered_tool" for d in n.decorator_list)]
    assert len(tools)==len(set(tools))
    assert set(tools)==set(catalogue())


def test_unknown_tool_fails_closed():
    def unknown():pass
    with pytest.raises(RuntimeError):register(MagicMock())()(unknown)


@pytest.mark.parametrize("name",["create_wire_from_to","move_component","delete_component"])
def test_disabled_legacy_never_connects(name):
    mod=wires if name=="create_wire_from_to" else components
    args=("A","B") if name=="create_wire_from_to" else (("A",1,2) if name=="move_component" else ("A",))
    with patch.object(mod,"_get_conn") as connect:
        assert getattr(mod,name)(*args)["status"]=="disabled"
    connect.assert_not_called()


def test_library_pagination_and_no_fabricated_names(tmp_path):
    for name in ["a","b","c"]:(tmp_path/(name+".dwg")).touch()
    data=symbol_library.list_symbols(library_path=str(tmp_path),limit=2)
    assert data["symbols"]==["a","b"] and data["next_offset"]==2 and data["total"]==3
    assert symbol_library.list_symbols(library_path=str(tmp_path),offset=2)["symbols"]==["c"]
    assert not symbol_library.list_symbols(library_path=str(tmp_path/"missing"))["success"]


@pytest.mark.parametrize("coords",[(0,0,0,0,1,1),(0,0,float("nan"),1,1,1)])
def test_invalid_dimension_never_writes(coords):
    with patch.object(dimensions,"target") as target:
        assert not dimensions.aligned("unused",*coords)["success"]
    target.assert_not_called()
