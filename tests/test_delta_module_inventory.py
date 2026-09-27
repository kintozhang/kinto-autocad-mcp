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


def test_remote_io_is_not_logic_controller_or_ethercat_pin_mapping():
    d=inventory()
    assert d["device_role"] == "ethercat_remote_io" and d["executes_plc_program"] is False
    assert d["intended_controller"] == "NC50E-FE" and d["logic_owner"] == "controller_internal_plc"
    assert d["communication"]["protocol"] == "EtherCAT"
    assert d["communication"]["physical_ports"] is None
    assert not d["communication"]["topology_verified"]


def test_smart_symbol_identity_mapping_covers_actual_attribute_convention():
    from src.tools.delta_module_inventory import expected_smart_symbol_connections
    from src.tools.delta_batch import verify_insert
    m=expected_smart_symbol_connections()
    assert len(m)==76
    assert m["X4TERM01"]=="TB2:X00" and m["X4TERM17"]=="TB3:X00"
    assert m["X1TERM33"]=="TB4:Y00" and m["X1TERM49"]=="TB5:Y00"
    assert m["X4TERM65"]=="TB4:C0" and m["X1TERM72"]=="TB5:C7"
    assert m["X8TERM76"]=="TB3:S/S"
    assert verify_insert({"connection_points":[{"connection":k,"terminal":v} for k,v in m.items()]})["success"]
    points=[{"connection":k,"terminal":v} for k,v in m.items()]
    points[0]["terminal"]="TB3:X00"
    with pytest.raises(RuntimeError):verify_insert({"connection_points":points})
