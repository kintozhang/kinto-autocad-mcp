import pytest
from src.tools.delta_io import plan


def inventory():
    return plan({"schema_version": 3, "purpose": "test_only", "module_id": "IO_TEST"})


def test_full_inventory_unique_and_unbound():
    data = inventory()
    points = [p for s in data["sections"] for p in s["terminals"]]
    assert len(points) == len({p["endpoint"] for p in points}) == 76
    assert sum(p["role"] == "input" for p in points) == 32
    assert sum(p["role"] == "output" for p in points) == 32
    assert sum(p["role"] == "relay_common" for p in points) == 8
    assert not data["ready_for_drawing"] and not data["cad_contacted"]
    assert all(p.get("global_plc_address") is None and p["potential"] is None for p in points)
    assert all(p["terminal"] != "N.C" for p in points)


def test_commons_and_duplicate_labels_remain_distinct():
    points = {p["endpoint"]: p for s in inventory()["sections"] for p in s["terminals"]}
    assert points["IO_TEST/TB2/X00"]["common_endpoint"] == points["IO_TEST/TB3/X00"]["common_endpoint"] == "IO_TEST/TB3/S/S"
    for tb, first in [("TB4", 0), ("TB5", 4)]:
        for ch in range(16):
            p = points[f"IO_TEST/{tb}/Y{ch:02d}"]
            assert p["common_endpoint"] == f"IO_TEST/{tb}/C{first + ch // 4}"
            assert p["electrical_type"] == "relay_no_dry_contact"
    assert points["IO_TEST/TB2/X00"]["subindex"] == 1
    assert points["IO_TEST/TB3/X00"]["subindex"] == 3


@pytest.mark.parametrize("change", [{"purpose":"production"}, {"module_id":""}, {"module_id":"a/b"}, {"global_plc_address":"X0"}])
def test_inventory_rejects_unsafe_or_extra_bindings(change):
    with pytest.raises(ValueError):
        plan({"schema_version":3, "purpose":"test_only", "module_id":"IO_TEST", **change})
